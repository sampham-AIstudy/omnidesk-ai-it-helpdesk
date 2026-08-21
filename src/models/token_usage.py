"""TokenUsageLog model — Bản ghi bất biến (immutable) cho mỗi lần gọi Mistral AI API, lưu số token và chi phí.
Sử dụng để ánh xạ bảng token_usage_log vào class TokenUsageLog (Kỹ thuật ORM)"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class TokenUsageLog(Base):
    """Bản ghi không thể thay đổi (immutable) cho mỗi lần gọi Mistral AI.

    Không được sửa đổi các bản ghi sau khi đã insert.
    Chi phí được tính tại thời điểm ghi để tránh làm sai lệch dữ liệu lịch sử
    khi bảng giá model thay đổi về sau.
    """

    __tablename__ = "token_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # user_id bắt buộc — cần thiết để giới hạn lượt gọi (rate-limit) và kiểm tra lạm dụng theo từng người dùng.
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,   # nullable để bản ghi vẫn tồn tại nếu user bị xóa khỏi hệ thống
        index=True,
    )

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Chi phí được tính trước tại thời điểm ghi (đơn vị USD); không bao giờ tính lại từ bảng giá hiện tại.
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationship lazy-load — không bắt buộc nhưng tiện khi cần JOIN với bảng users trong ORM.
    user = relationship("User", foreign_keys=[user_id], lazy="select")
