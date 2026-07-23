# Maggie 项目记忆文档

> **用途**：持久化项目上下文和决策记录，避免每次会话从原始代码重新探索。
> **更新规则**：每次做出新的决策或完成变更后，必须同步更新此文档。
> **最后更新**：2026-07-24 — Phase A 完成

---

## 1. 项目身份

- **名称**：Maggie — 工程合同及请款管理系统 (Engineering Contract & Payment Application Management System)
- **仓库**：https://github.com/PMPai/maggie
- **分支**：`phase1-core-loop`
- **定位**：面向工程建设企业（财务、项目经理、造价、审核人员）的多项目、多角色计价请款平台
- **核心能力**：合同版本管理 → 请款计算 → 审批过账 → 发票收款 → 文档生成完整闭环
- **规格文档**：`Prompt.md`（1775 行，完整需求规格）

---

## 2. 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 前端 | Next.js 14 (React + TypeScript), Tailwind CSS | Node 20 |
| 后端 | FastAPI, SQLAlchemy 2.x (async), Pydantic v2 | Python 3.12 |
| 数据库 | PostgreSQL 16 + pgvector | Docker |
| 缓存/消息 | Redis 7 | Docker |
| 异步任务 | Celery 5.4.0（**尚未启用 worker**） | requirements.txt 已含 |
| PDF 生成 | Playwright 1.49.1（**Docker 内未安装**） | requirements.txt 已含 |
| Excel | openpyxl 3.1.5 | |
| 部署 | Docker Compose | 4 服务: postgres, redis, api, frontend |

---

## 3. 当前完成状态

- **Phase 1 + 2 + 3 全部完成**
- 16 个数据库迁移
- 52 项测试通过（20 项规格测试 + 32 项单元测试）
- 17 个测试文件在 `backend/tests/`
- 16 个 API 路由在 `backend/app/api/`
- 工作树干净，无未提交变更

### 3.1 后端结构

```
backend/app/
├── api/                    # 16 个路由: auth, companies, projects, contracts,
│                           #   documents, payment_applications, approvals,
│                           #   standard_items, variations, deductions,
│                           #   retention_entries, invoices, collections,
│                           #   financial_adjustments, item_mappings,
│                           #   matching_reviews, reports
├── auth/
├── config.py               # Pydantic Settings, 无 OCR/Celery 设置
├── db/
├── deps.py
├── main.py                 # FastAPI app, CORS, 安全头, 限流中间件
├── models/
├── schemas/
├── security/               # rate_limit.py
└── services/
    ├── calc_engine.py      # 计算引擎（纯函数, 可单测）
    ├── file_service.py     # 文件上传/下载, SHA-256, 路径穿越防护
    ├── approval_service.py
    ├── collection_service.py
    ├── deduction_service.py
    ├── retention_service.py
    ├── variation_service.py
    ├── docgen/
    │   ├── pdf.py          # Playwright async → A4 PDF（Docker 内会失败）
    │   └── excel.py        # openpyxl Excel 生成
    ├── llm/
    │   ├── protocol.py     # LLMResult, LLMCandidate
    │   ├── stub.py         # StubClient (LLM_ENABLED=false 时)
    │   └── openai_impl.py  # OpenAI 兼容客户端
    ├── matching/
    │   ├── pipeline.py     # 完整管线: normalize→alias→rule→fulltext→vector→LLM
    │   ├── normalize.py
    │   ├── alias.py
    │   ├── rule.py
    │   ├── fulltext.py
    │   └── vector.py
    └── ocr/
        └── adapter.py      # Stub OCR (返回空结果, is_available=False)
```

### 3.2 前端结构

```
frontend/app/
├── page.tsx                # 登录页
├── dashboard/page.tsx      # 管理驾驶舱（基础版, 未显示完整指标）
├── projects/[id]/
│   ├── page.tsx            # 项目详情（10 个标签页, 多数为简单表格/空状态）
│   ├── catalog/            # 标准项目
│   ├── deductions/         # 扣款台账
│   ├── invoices/           # 发票收款
│   ├── mapping/            # 映射
│   ├── retention/          # 保留款台账
│   └── variations/         # 变更台账
├── applications/
│   ├── new/                # 新建请款向导
│   └── [id]/               # 请款详情
├── reports/                # 报表页
└── audit/                  # 审计页
```

### 3.3 关键文件路径

| 文件 | 用途 | 状态 |
|------|------|------|
| `backend/app/services/docgen/pdf.py` | Playwright HTML→PDF | 代码正确, Docker 内缺 Chromium+字体 |
| `backend/Dockerfile` | API 容器构建 | Playwright 安装被注释 |
| `docker-compose.yml` | 服务编排 | worker 服务被注释 |
| `backend/app/services/ocr/adapter.py` | OCR 适配器 | Stub, 返回空 |
| `backend/app/config.py` | 配置 | 无 OCR/Celery 设置 |
| `templates/billing/default.html` | 请款单 HTML 模板 | 完整, A4 打印样式 |

---

## 4. 已知缺口（来自 README + 代码探索）

| # | 缺口 | 影响 | 阶段规划 |
|---|------|------|----------|
| 1 | Celery Worker 未实现（`app/tasks/` 不存在） | 异步任务无法运行 | **Phase A (当前)** |
| 2 | PDF 生成在 Docker 内失败（Playwright+字体） | 无法生成请款单 PDF | **Phase A (当前)** |
| 3 | OCR 为 stub（返回空） | 历史文件无法自动提取 | **Phase A (当前)** |
| 4 | Dashboard 未显示完整驾驶舱指标 | 管理层看不到全貌 | Phase B |
| 5 | 文件收件箱页面缺失 (spec 8.3) | 文件上传/识别无界面 | Phase B |
| 6 | 合同抽取审核页面缺失 (spec 8.5) | 左右并排审核无界面 | Phase B |
| 7 | Master Budget 视图缺失 (spec 8.6) | 预算对比无界面 | Phase B |
| 8 | 审批与异常中心不完整 (spec 8.10) | 集中审批无界面 | Phase B |
| 9 | 报表页面不完整 (spec 8.14) | 11 种报表未实现 | Phase B |
| 10 | E2E 测试未实现 | Playwright Docker 安装问题 | Phase C |
| 11 | 扩展集成测试覆盖不足 | | Phase C |

---

## 5. 当前工作：Phase A — 后端关键缺口补齐

> **状态**：✅ 已完成（2026-07-24）
> **范围**：A1 Celery + A2 PDF 修复 + A3 OCR，三项一起完成
> **分支**：`phase-a-celery-pdf-ocr`（11 commits）
> **测试**：70 passed, 0 failed, 0 skipped（52 原有 + 18 新增）

### 5.1 已确认的决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 完善方向 | 全面完善（分阶段） | 先修关键缺口 → 补前端 → 补测试 |
| 阶段 A 范围 | A1+A2+A3 一起做 | 三项关联紧密 |
| PDF 方案 | **修复 Playwright + 手动字体** | 保留 Chromium 渲染质量, pdf.py 代码不变, 符合规格 |
| OCR 方案 | **Tesseract 默认 + 可切换云** | 自托管免费, 支持中文, 隐私安全, 可配置切换 |
| Celery 方案 | **务实 Celery（方案 1）** | PDF+OCR+LLM 入 Celery, 文件哈希保持同步 |

### 5.2 设计 — 已确认的章节

#### 5.2.1 架构总览（已确认 ✓）

```
Frontend ──▶ FastAPI ──▶ PostgreSQL
                  │
                  │ submit task (delay)
                  ▼
              Redis (broker+backend) ◀──▶ Celery Worker
                                            │
                                  ┌─────────┼─────────┐
                                  ▼         ▼         ▼
                            Playwright  Tesseract  LLM API
                            (PDF gen)   (OCR)      (httpx)
```

三个异步任务流：
1. **PDF/Excel 生成**：API 提交 Celery → Worker 调 docgen → 存文件+创建 generated_documents 记录 → 前端轮询
2. **OCR 提取**：文件上传后提交 → Worker 调 OCRAdapter.extract() → 更新 documents.ocr_status → 前端轮询
3. **LLM 匹配**：pipeline 返回候选后提交 → Worker 调 LLM API → 存 matching_reviews → 前端轮询

#### 5.2.2 组件设计（已确认 ✓）

**Celery 模块**：
```
backend/app/tasks/
├── __init__.py          # 导出 celery_app
├── celery_app.py        # Celery 实例 + 配置
└── tasks.py             # 3 个任务: generate_document, run_ocr, run_llm_match
```

Celery 配置：
- broker/backend = REDIS_URL
- task_track_started=True, task_time_limit=300
- task_acks_late=True（worker 宕机任务不丢失）
- retry_backoff=True, retry_backoff_max=60

**OCR 适配器重设计**：
```
backend/app/services/ocr/
├── __init__.py           # get_ocr_adapter() 工厂
├── protocol.py           # OCRAdapter 协议 + OCRResult
├── tesseract.py          # Tesseract 实现 (pytesseract + Pillow + pdf2image)
├── cloud.py              # 云 OCR stub（后续可接入 Google Vision/Azure）
└── stub.py               # 默认 stub
```

工厂：`get_ocr_adapter(settings)` 按 `OCR_PROVIDER` 环境变量返回对应适配器

**Dockerfile 变更**：
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libpq-dev gcc curl \
    fonts-noto-cjk fonts-liberation \
    tesseract-ocr tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*
RUN pip install playwright==1.49.1 && playwright install chromium
```

**任务状态 API**：新增 `app/api/tasks.py`
- `GET /tasks/{task_id}/status` → `{state, result, error}`
- 仅认证用户可查询

**Config 新增**：
```python
OCR_PROVIDER: str = "none"        # "tesseract" | "cloud" | "none"
OCR_TESSERACT_LANG: str = "chi_sim+eng"
OCR_CLOUD_API_KEY: str = ""
OCR_CLOUD_ENDPOINT: str = ""
```

#### 5.2.3 数据流与错误处理（已确认 ✓）

- API 永不阻塞在耗时操作上——提交任务后立即返回 task_id
- 错误处理：Playwright 失败→FAILURE+可重试; OCR 失败→ocr_status=FAILED+不影响上传; LLM 失败→非 LLM 候选仍可用
- 优雅降级：LLM_ENABLED=false 跳过 LLM; OCR_PROVIDER=none 跳过 OCR; Playwright 未安装→API 层预检返回 503
- 前端轮询：指数退避 1s→5s 上限
- 幂等：PDF 检查已有 is_final 记录; OCR 检查 ocr_status; LLM 检查未审核 matching_reviews

### 5.3 设计 — 全部章节已确认 ✓

- [x] 第 1 节：架构总览
- [x] 第 2 节：组件设计（Celery + OCR + PDF + API + Config）
- [x] 第 3 节：数据流与错误处理
- [x] 第 4 节：Docker Compose 与依赖变更
- [x] 第 5 节：测试策略

### 5.4 Spec 文档

- **路径**：`docs/superpowers/specs/2026-07-23-phase-a-celery-pdf-ocr-design.md`
- **状态**：已写入，已自审（修复 1 处 Dockerfile 缺 poppler-utils 的不一致），待用户审核
- **自审结果**：无占位符、无矛盾（已修复）、范围聚焦、无歧义

### 5.5 实现状态

- [x] Spec 已写入并审核通过
- [x] 实现计划已写入：`docs/superpowers/plans/2026-07-23-phase-a-celery-pdf-ocr.md`
- [x] 10 个 Task 全部完成（TDD 方式）

### 5.6 实现结果

| 组件 | 状态 | 验证 |
|------|------|------|
| Celery Worker | ✅ 运行中 | `celery@... ready` in worker logs |
| PDF 生成 (Playwright) | ✅ 可用 | 2 integration tests pass, Chinese font rendering |
| OCR (Tesseract) | ✅ 可用 | tesseract 5.5.0, test_tesseract_extract_from_image passes |
| OCR (Cloud stub) | ✅ 可用 | CloudOCRAdapter stub with httpx |
| Task Status API | ✅ 可用 | `GET /api/tasks/{task_id}/status` |
| Generate Endpoint | ✅ 可用 | `POST /payment-applications/{id}/generate` |
| Matching Pipeline | ✅ 重构 | LLM 移至 Celery task, pipeline 仅做 alias/rule/fulltext/vector |

### 5.7 新增文件

```
backend/app/tasks/
├── __init__.py          # exports celery_app
├── celery_app.py        # Celery instance + config
└── tasks.py             # 3 tasks: generate_document, run_ocr, run_llm_match

backend/app/services/ocr/
├── __init__.py           # get_ocr_adapter() factory
├── protocol.py           # OCRResult + OCRAdapter Protocol
├── stub.py               # StubOCRAdapter
├── tesseract.py          # TesseractAdapter (pytesseract + pdf2image)
└── cloud.py              # CloudOCRAdapter (httpx, for future cloud OCR)

backend/app/api/tasks.py   # Task status API
backend/tests/test_celery_tasks.py
backend/tests/test_ocr_adapter.py
backend/tests/test_task_api.py
backend/tests/test_pdf_docker.py
```

### 5.8 关键修复

1. **Playwright host deps**: 不用 `--with-deps`（Debian 12 字体包不存在），手动安装 18 个库（libdbus-1-3, libatk1.0-0, libnss3 等）
2. **模板路径**: `templates/` 目录在 backend build context 外，通过 docker-compose volume mount 解决
3. **Celery tasks engine.dispose()**: 使用 try/finally 确保 SQLAlchemy async engine 正确释放
4. **ApplicationStatus 枚举**: 不是字符串比较，使用 `ApplicationStatus.POSTED` 枚举值

### 5.9 Commits

```
561bddc test: PDF generation integration test with Playwright (Phase A)
6b26abc feat: Docker worker service + Playwright fonts + Tesseract OCR (Phase A)
aa95cb1 refactor: move LLM matching from inline to Celery task (Phase A)
60b7471 feat: task status API + document generation endpoint (Phase A)
54e41b4 feat: Celery tasks for PDF generation, OCR, and LLM matching (Phase A)
e8c172b feat: Celery app instance with Redis broker (Phase A)
5413ccb feat: Cloud OCR adapter stub for future cloud API integration (Phase A)
061b243 feat: Tesseract OCR adapter with PDF and image support (Phase A)
f86b58a fix: address code review — remove unused import, add factory tests, type hints (Phase A)
b23191b feat: OCR adapter protocol + stub + factory (Phase A)
83f2887 docs: Phase A spec, plan, and memory.md
```

---

## 6. 后续阶段规划

### Phase B：前端核心页面补全
- B1. Dashboard 驾驶舱完整指标（spec 8.2）
- B2. 文件收件箱（spec 8.3）
- B3. 合同抽取审核（spec 8.5，左右并排）
- B4. Master Budget 视图（spec 8.6）
- B5. 审批与异常中心（spec 8.10）
- B6. 报表页面完善（spec 8.14）

### Phase C：测试与质量
- C1. Playwright E2E 测试
- C2. 扩展集成测试
- C3. 备份一致性验证

---

## 7. 关键业务约束（来自规格 RESTRAIN 部分）

1. 不得使用浮点数计算财务金额（用 DECIMAL）
2. 不得覆盖已过账请款/历史合同版本/原始合同文件
3. 不得让 LLM 计算金额/成本/税额/保留款或自动审批
4. 不得将未批准变更加入可请款余额
5. 不得将发票金额和实际收款差异静默抹平
6. 不得把服务器绝对文件路径发送给前端
7. 不得使用真实客户数据调用外部 LLM，除非明确配置并授权
8. 所有高风险操作必须有确认+权限检查+审计记录
9. 计算引擎、文件服务、LLM 服务、审批服务、文档生成服务必须分离

---

## 8. 示例数据

| 项目 | 合同 | 说明 |
|------|------|------|
| 25-032 | CQ880A-11501 | 2 合同版本, 6 明细, 3 期请款, 保留款释放 980,496, 2 笔扣款 71,000 |
| 24-023 | FS11308001 | 38,980,000 含税总价, 树状明细, 多单位 |

默认账号：`admin@maggie.local / admin123`
