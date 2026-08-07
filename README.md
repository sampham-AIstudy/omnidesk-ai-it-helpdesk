# 🤖 AI20K Agent Template

Template chính thức cho học viên **VinUni AI20K Build Phase** — cung cấp sẵn cấu trúc dự án, code mẫu, và hướng dẫn kỹ thuật chi tiết để xây dựng AI Agent đạt điểm cao (35+/50).

> 📖 **Technical Guidebook:** [phoenix.note.transformerlabs.ai/technical-book](https://phoenix.note.transformerlabs.ai/technical-book)

## 🎯 Template này dùng để làm gì?

Khi tham gia AI20K Build Phase, mỗi đội cần xây dựng một AI Agent hoàn chỉnh — từ kiến trúc, code, test, đến deploy. Thay vì bắt đầu từ con số không, template này cung cấp:

- **Cấu trúc thư mục chuẩn** — đã được thiết kế theo best practices (separation of concerns)
- **Code mẫu** cho các phần cốt lõi: LangGraph agent, FastAPI API, config, schemas
- **Docker + CI/CD sẵn** — Dockerfile multi-stage, GitHub Actions workflow
- **Hướng dẫn kỹ thuật 10 chương** — từ clone template đến nộp bài Demo Day
- **Checklist 10 deliverables** — đảm bảo không bỏ sót yêu cầu BTC
- **AI Usage Logging tự động** — Pre-configured hooks cho Claude Code, Cursor, Codex, Gemini CLI, Antigravity, và GitHub Copilot

## ⚡ Quick Start

### Bước 1: Fork hoặc Clone

```bash
# Clone template
git clone https://github.com/AI20K-Build-Cohort-2/starter-code-template.git team-YOUR_TEAM_NAME
cd team-YOUR_TEAM_NAME

# Xóa git history cũ và khởi tạo lại
rm -rf .git
git init
git add .
git commit -m "feat: khởi tạo dự án từ template"
```

### Bước 2: Setup môi trường

```bash
# Tạo virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Cài dependencies
pip install -e ".[dev]"

# Cấu hình API keys
cp .env.example .env
# Mở .env và thêm MISTRAL_API_KEY của bạn
# Đồng thời cập nhật AI_LOG_API_KEY bằng key riêng từ link mời của BTC
# (giá trị trong .env.example chỉ là placeholder)
```

### Bước 3: Cài AI Logging Hooks

```bash
# Linux / macOS / Git Bash
bash scripts/setup_hooks.sh

# Windows PowerShell
# powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
```

Hooks tự động log mọi AI prompt khi dùng Claude Code, Cursor, Codex, Gemini CLI, Antigravity, hoặc GitHub Copilot. Không cần thao tác thủ công.

### Bước 4: Chạy server

# Backend
.venv\Scripts\activate
python run.py


# Frontend
cd frontend
npm run dev


### Bước 5: Đọc hướng dẫn

📖 Mở **[Technical Guidebook](https://phoenix.note.transformerlabs.ai/technical-book)** và làm theo từng chương.

## 📁 Cấu trúc dự án

```
├── src/
│   ├── agents/           # 🧠 LangGraph Agent
│   │   ├── graph.py      #    State graph (nodes + edges)
│   │   ├── state.py      #    State schema (TypedDict)
│   │   ├── nodes/        #    Node functions (classifier, RAG, HITL, router, auto_close)
│   │   └── tools/        #    Agent tools (@tool)
│   ├── api/              # 🌐 FastAPI Backend
│   │   ├── auth.py       #    JWT Auth (/login, /me)
│   │   ├── tickets.py    #    Ticket CRUD + HITL approve/reject
│   │   ├── analytics.py  #    Dashboard metrics, SLA alerts, Audit log
│   │   ├── admin.py      #    User & Knowledge Base management
│   │   └── routes.py     #    API routes aggregator
│   ├── models/           # 📋 SQLAlchemy & Pydantic schemas
│   ├── services/         # 🔧 Business logic (Auth, Ticket, RAG, LLM)
│   ├── data/             # 💾 Knowledge base seed (35 KB entries)
│   ├── config.py         # ⚙️ Pydantic Settings
│   └── main.py           # 🚀 FastAPI app entry point
├── frontend/             # ⚛️ Next.js 16 Web Application (Enterprise light UI)
│   ├── src/app/          #    App Router (Employee, Technician, Manager, Admin portals)
│   ├── src/components/   #    UI primitives + Sidebar, HITL, TicketCard, AI processing
│   └── src/lib/          #    API client, Zustand authStore, labels/confidence utilities
├── data/                 # 💾 Database & Datasets
│   ├── helpdesk_tickets.csv # 📊 Kaggle Dataset (1M tickets)
│   ├── helpdesk.db       #    SQLite database
│   └── chroma/           #    Vector DB persistence
├── tests/                # 🧪 pytest suite
│   ├── test_agents/      #    Agent/graph unit tests
│   └── test_api/         #    API endpoint tests
├── scripts/              # 🔌 Utility & AI Logging Hooks
│   ├── import_kaggle_dataset.py # Script import Kaggle CSV vào DB
│   ├── log_hook.py       #    Auto-log cho Claude/Cursor/Codex/Gemini/Copilot
│   ├── log_antigravity.py#    Antigravity IDE prompt scanner
│   └── setup_hooks.sh    #    One-time hook installer
├── docs/
│   ├── guide/            # 📖 Technical Guidebook (10 chapters)
│   └── architecture_diagram.md
├── eval/                 # 📊 Evaluation results & benchmark
│   └── classification_eval.py
├── presentation/         # 🎤 Demo Day slides
├── Dockerfile            # 🐳 Multi-stage backend build
├── docker-compose.yml    # 🐙 Full stack orchestration (Backend + Frontend)
└── pyproject.toml        # ⚙️ Python project configuration
```

## 🧭 Quy ước trải nghiệm IT Help Desk

- Giao diện dùng phong cách enterprise sáng, tiếng Việt, responsive cho bốn cổng Nhân viên, Kỹ thuật viên, Quản lý và Quản trị.
- Ba dải độ tin cậy AI theo PRD FR-09 được dùng thống nhất ở backend và frontend:
  - `>= 75%`: đủ điều kiện xử lý bình thường hoặc tự đóng nếu mọi rule an toàn khác đều cho phép.
  - `60–74%`: cảnh báo; người dùng có thể thử giải pháp hoặc yêu cầu IT Support trực tiếp.
  - `< 60%`: bắt buộc HITL/xử lý thủ công.
- Production, VIP và category nhạy cảm là điều kiện HITL độc lập, không bị bỏ qua khi confidence cao.
- Modal “AI đang xử lý” lấy trạng thái thật từ `GET /tickets/{id}`; không mô phỏng tiến trình bằng timer.
- Màn hình client có skeleton, error/retry và route-level loading/error theo quy ước Next.js 16.

Có thể override các ngưỡng qua `.env`, nhưng phải giữ `HITL <= WARNING <= AUTO_CLOSE`; cấu hình mặc định nằm trong `.env.example`.

## 📚 Technical Guidebook — 10 Chương

| Chương | Nội dung | Thời gian |
|---------|----------|-----------|
| 1 | Lời mở đầu — Mục tiêu, cách sử dụng | 15 phút |
| 2 | Khởi tạo dự án — Clone, setup, git workflow | 4 giờ |
| 3 | Thiết kế kiến trúc — 3-tier, diagrams, ADR | 6 giờ |
| 4 | **LangGraph Agent** — State, nodes, edges, tools, RAG | 8 giờ |
| 5 | FastAPI — Routes, validation, error handling, streaming | 6 giờ |
| 6 | Giao diện — Next.js + Streamlit quickstart | 6 giờ |
| 7 | DevOps — Docker, CI/CD, deploy, logging | 6 giờ |
| 8 | Kiểm thử — Unit test, integration test, RAGAS | 4 giờ |
| 9 | Demo Day — 10 deliverables, checklist, tips | 2 giờ |
| 10 | Tài nguyên — Khóa học, docs, BMAD method | tham khảo |

📖 **Đọc online:** [phoenix.note.transformerlabs.ai/technical-book](https://phoenix.note.transformerlabs.ai/technical-book)

## 📋 10 Deliverables cho Demo Day

| # | Deliverable | File vị trí | Template có sẵn |
|---|-------------|-------------|:---:|
| 1 | Source Code | `src/` | ✅ |
| 2 | README.md | `README_boilerplate.md` → copy thành `README.md` | ✅ |
| 3 | Architecture Diagram | `docs/architecture_diagram.md` | ✅ |
| 4 | AI Logs | LangSmith (3 env vars) + Auto AI Usage Logging | ✅ |
| 5 | Live URL | Deploy lên Render/Vercel | ⚡ CI/CD sẵn |
| 6 | Video Demo | `presentation/` | 📝 |
| 7 | Pitch Deck | `presentation/` | 📝 |
| 8 | Development Journal | `JOURNAL.md` | ✅ |
| 9 | Worklog | `WORKLOG.md` | ✅ |
| 10 | Evaluation Evidence | `eval/` | 📝 |

## 🛠 Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| AI Agent | LangGraph + LangChain | Latest |
| Backend | FastAPI + Uvicorn | 0.100+ |
| LLM | Mistral Small / Codestral | API |
| Frontend | Next.js / Streamlit | 14+ / 1.30+ |
| Database | SQLite (dev) / PostgreSQL (prod) | — |
| DevOps | Docker + GitHub Actions | — |
| Testing | pytest + pytest-asyncio | 8+ |

## Cấu hình provider và cache

Ứng dụng dùng Mistral làm provider LLM duy nhất và embedding multilingual chạy local.
Các key Gemini, Cohere, Voyage và Tavily không được tích hợp vì chúng trùng chức năng,
trong khi benchmark retrieval 12 tình huống hiện tại đạt Hit@1/Hit@3 100%. Việc không
gửi ticket và KB qua thêm provider cũng giảm dependency, chi phí và bề mặt rò rỉ dữ liệu.

`REDIS_URL` được dùng làm LLM cache chính vì tương thích với Redis managed hoặc Redis
tự host. Nếu kết nối này lỗi, ứng dụng thử `UPSTASH_REDIS_REST_URL` cùng
`UPSTASH_REDIS_REST_TOKEN`; nếu cả hai không dùng được, hệ thống vẫn chạy và bỏ qua
cache. Endpoint `/health` chỉ trả hostname, không trả username, password hay token.

```env
REDIS_URL=rediss://user:password@redis-host:6380/0
REDIS_CACHE_TTL=3600
```

## Làm giàu Knowledge Base từ tài liệu chính thức

Danh mục nguồn được allow-list tại `scripts/it_helpdesk_sources.json`. Crawler kiểm tra
`robots.txt`, không tự đi theo liên kết, giới hạn dung lượng, khử trùng lặp và lưu URL,
thời điểm thu thập cùng SHA-256 cho từng đoạn tài liệu.

```bash
# Chỉ crawl và lưu data/enriched_helpdesk_kb.json
python scripts/crawl_helpdesk_kb.py

# Crawl và upsert trực tiếp các đoạn đã chuẩn hóa vào ChromaDB
python scripts/crawl_helpdesk_kb.py --index

# Hoặc chỉ index lại file đã crawl, không truy cập Internet
python scripts/crawl_helpdesk_kb.py --index-only

# Rebuild toàn bộ KB + historical memory + tài liệu crawl
python scripts/rebuild_rag_index.py

# Đánh giá retrieval tiếng Việt (Hit@1, Hit@3, MRR)
python eval/rag_retrieval_eval.py

# Đánh giá RAGAS-style trên golden dataset đa dạng
python eval/ragas_assessment_eval.py

# Đánh giá đủ context coverage + faithfulness + answer focus bằng câu trả lời sinh từ LLM
# Lưu ý: lệnh này gửi câu hỏi golden + context KB đã retrieve tới provider LLM trong .env
python eval/ragas_assessment_eval.py --generate-answers

# Nếu đã cấu hình evaluator LLM cho RAGAS, chạy thêm official RAGAS metrics
python eval/ragas_assessment_eval.py --generate-answers --use-ragas
```

Golden dataset nằm ở `eval/ragas_golden_dataset.json`, gồm câu hỏi trực tiếp, mơ hồ, đánh đố,
ngoài phạm vi tài liệu, prompt injection, yêu cầu bypass security/approval và case phân quyền.
Report sinh ra tại `eval/results/ragas_assessment_report.json`, `eval/results/ragas_assessment_report.md`
và `eval/results/ragas_dataset.json` theo schema `question/answer/contexts/ground_truth` để đưa vào RAGAS.

Hệ thống dùng `paraphrase-multilingual-MiniLM-L12-v2` và collection riêng
`helpdesk_kb_multilingual_v1`. Khi đổi embedding model phải dùng collection mới,
không trộn vector được tạo bởi các model khác nhau.

Nên chạy lại định kỳ và review các mục trong `failures` trước khi dùng cho production.

## 📊 AI Usage Logging

Template đã tích hợp sẵn auto-logging hooks cho 6 AI tools:

| Tool | Cơ chế | Config |
|------|--------|--------|
| Claude Code | `.claude/settings.json` hooks | Tự động |
| Cursor | `.cursor/hooks.json` | Tự động |
| OpenAI Codex CLI | `.codex/hooks.json` | Tự động |
| Gemini CLI | `.gemini/settings.json` | Tự động |
| GitHub Copilot | `.github/hooks/hooks.json` | Tự động |
| Antigravity IDE | Pre-push scan transcript | Tự động trên `git push` |

Tất cả prompts và tool calls được log vào `.ai-log/session.jsonl` và tự động submit lên grading server mỗi khi `git push`.

**ChatGPT / web tools khác** — log thủ công:
```bash
bash scripts/_pyrun.sh scripts/log_manual.py --tool chatgpt --prompt "What you asked"
```

> ⚠️ Chạy `bash scripts/setup_hooks.sh` một lần sau khi clone để cài pre-push hook.

## 📖 Đọc Technical Guidebook

**Online (khuyến nghị):** [phoenix.note.transformerlabs.ai/technical-book](https://phoenix.note.transformerlabs.ai/technical-book)

Đăng nhập bằng GitHub (cùng account đã được BTC mời vào org `AI20K-Build-Cohort-2`)
→ chọn tab **Technical Book** ở sidebar trái → đọc 10 chương + topic sections,
có table of contents bên phải, hỗ trợ light/dark/cyberpunk theme.

**Offline:** mọi chương đều ở thư mục `docs/guide/` trong template này — mở bằng
bất kỳ markdown viewer/editor nào (VS Code, Obsidian, GitHub UI, …).

## 🔗 Liên kết

- 📖 **Technical Guidebook:** [phoenix.note.transformerlabs.ai/technical-book](https://phoenix.note.transformerlabs.ai/technical-book)
- 🏫 **AI20K Program:** VinUni AI20K Build Phase
- 👨‍🏫 **Mentor:** Đặng Hải Lộc

## 📄 License

MIT — Sử dụng tự do cho mục đích giáo dục.


