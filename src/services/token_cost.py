from __future__ import annotations
"""Dịch vụ tính chi phí token — Tra cứu bảng giá, tính toán chi phí và ghi log bất đồng bộ vào DB.

Ghi chú thiết kế:
- MISTRAL_PRICING là dict in-memory; luôn dùng .get() kèm fallback "default"
  để tên model không tồn tại trong bảng không bao giờ gây ra KeyError.
- Chi phí được tính ngay sau khi nhận phản hồi API, sau đó lưu thành bản ghi bất biến.
  Chi phí KHÔNG BAO GIỜ được tính lại khi xem báo cáo để bảo toàn tính chính xác của dữ liệu lịch sử.
- record_token_usage_async chạy trong background task của asyncio với session DB riêng biệt,
  đảm bảo không làm chậm hoặc block request của người dùng.
"""


import asyncio
import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bảng giá tra cứu (USD trên 1 triệu token, cập nhật Q3-2025)
# Nguồn: https://mistral.ai/technology/#pricing
# ---------------------------------------------------------------------------
MISTRAL_PRICING: dict[str, dict[str, float]] = {
    "mistral-small-2506":    {"input_cost_per_1m": 0.1,  "output_cost_per_1m": 0.3},
    "mistral-small-2603":    {"input_cost_per_1m": 0.15, "output_cost_per_1m": 0.6},
    "ministral-3b-2512":     {"input_cost_per_1m": 0.1,  "output_cost_per_1m": 0.1},
    "ministral-8b-2512":     {"input_cost_per_1m": 0.15, "output_cost_per_1m": 0.15},
    "ministral-14b-2512":    {"input_cost_per_1m": 0.2,  "output_cost_per_1m": 0.2},
    "mistral-large-2512":    {"input_cost_per_1m": 0.5,  "output_cost_per_1m": 1.5},
    # Giá mặc định — dùng khi tên model không có trong bảng trên.
    "default":               {"input_cost_per_1m": 0.2,  "output_cost_per_1m": 0.6},
}


def calculate_mistral_cost(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Tính chi phí ước tính (USD) cho một lần gọi API.

    Dùng .get() an toàn với fallback "default" để tên model không nhận ra
    không bao giờ gây ra KeyError và làm crash ứng dụng.
    """
    pricing = MISTRAL_PRICING.get(model_name) or MISTRAL_PRICING["default"]
    input_cost  = (prompt_tokens     / 1_000_000) * pricing["input_cost_per_1m"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output_cost_per_1m"]
    return round(input_cost + output_cost, 8)


def extract_token_counts(ai_message) -> tuple[int, int]:
    """Trích xuất an toàn (prompt_tokens, completion_tokens) từ AIMessage.

    Trả về (0, 0) khi usage_metadata vắng mặt hoặc bị lỗi — đảm bảo
    caller không bao giờ crash dù provider không cung cấp dữ liệu usage.
    """
    try:
        meta = getattr(ai_message, "usage_metadata", None) or {}
        prompt_tokens     = int(meta.get("input_tokens",  0))
        completion_tokens = int(meta.get("output_tokens", 0))
        return prompt_tokens, completion_tokens
    except Exception:
        return 0, 0


async def _write_token_log(
    user_id: int | None,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    estimated_cost: float,
) -> None:
    """Ghi một bản ghi TokenUsageLog vào DB bằng session riêng biệt (isolated).

    Hàm này luôn được gọi qua asyncio.create_task() để mọi độ trễ của DB
    hoàn toàn tách biệt khỏi chu kỳ request/response của người dùng.
    """
    from src.database import AsyncSessionLocal
    from src.models.token_usage import TokenUsageLog

    try:
        async with AsyncSessionLocal() as session:
            log = TokenUsageLog(
                user_id=user_id,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost=estimated_cost,
                created_at=datetime.now(UTC),
            )
            session.add(log)
            await session.commit()
            logger.debug(
                "[TokenCost] Đã ghi log: model=%s prompt=%d completion=%d cost=$%.6f user_id=%s",
                model_name, prompt_tokens, completion_tokens, estimated_cost, user_id,
            )
    except Exception as exc:
        # Không bao giờ để lỗi ghi log lan sang request của người dùng.
        logger.warning("[TokenCost] Không thể ghi log token usage vào DB: %s", exc)


def dispatch_token_logging(
    ai_message,
    model_name: str,
    user_id: int | None,
) -> None:
    """Trích xuất token usage từ AIMessage và kích hoạt background task ghi log.

    An toàn khi gọi từ cả context đồng bộ lẫn bất đồng bộ.
    Bỏ qua im lặng nếu gọi ngoài event loop đang chạy (ví dụ: unit test không có event loop).

    Cách dùng (trong bất kỳ async endpoint hoặc node nào sau llm.ainvoke()):
        response = await llm.ainvoke(messages)
        dispatch_token_logging(response, model_name="mistral-large-latest", user_id=current_user.id)
    """
    try:
        prompt_tokens, completion_tokens = extract_token_counts(ai_message)
        if prompt_tokens == 0 and completion_tokens == 0:
            # Không có dữ liệu usage — bỏ qua im lặng để tránh ghi hàng loạt bản ghi zero-cost.
            return

        estimated_cost = calculate_mistral_cost(model_name, prompt_tokens, completion_tokens)

        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(
                _write_token_log(
                    user_id=user_id,
                    model_name=model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    estimated_cost=estimated_cost,
                )
            )
        else:
            logger.debug("[TokenCost] Không có event loop đang chạy; bỏ qua dispatch log bất đồng bộ.")
    except Exception as exc:
        logger.warning("[TokenCost] Lỗi trong dispatch_token_logging (không nghiêm trọng): %s", exc)
