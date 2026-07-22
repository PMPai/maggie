# 工程合同及请款管理系统 (Maggie)

Engineering Contract & Payment Application Management System — a multi-project, multi-role billing platform for construction firms. Handles contracts with versioned line items, progress payment applications, retention ledgers, variations, deductions, approvals, idempotent posting, invoice/collection tracking, standard item matching, optional LLM semantic matching, and PDF/Excel document generation.

---

## 1. 系统目的 (System Purpose)

本系统面向工程建设企业的财务、项目经理、造价及审核人员，提供从合同录入、项目映射、请款计算、审批过账到发票收款的完整闭环管理。核心能力包括：

- **合同版本管理**：支持多版本合同，版本不可覆盖，历史可追溯。
- **变更单台账**：合同变更（数量/金额调整）独立管理，需审批后才纳入可请款量。
- **请款计算引擎**：纯函数计算，支持数量制、总价制、里程碑制、百分比制，自动处理保留款、扣款、税额及舍入。
- **保留款完整台账**：HOLD/RELEASE/ADJUSTMENT/REVERSAL 分类账，余额 = SUM(entries)，无可变余额列。
- **扣款台账**：多类型扣款（预付款抵扣、材料扣款、质量罚款等）+ 税务处理。
- **发票与收款**：发票登记、收款分配、差异核销（不自动调整）。
- **标准项目匹配**：别名 + 规则 + 全文检索 + 向量（pgvector）+ 可选 LLM 语义建议。
- **审批工作流**：可配置多级审批（项目负责人 → 财务复核），过账幂等且不可逆。
- **文档生成**：Playwright 生成 A4 可打印 PDF，openpyxl 生成 Excel，数据与数据库一致。
- **项目级权限隔离**：用户仅能访问所属项目数据，URL 切换无法绕过。

---

## 2. 技术架构 (Tech Architecture)

| 层 | 技术 | 说明 |
|---|---|---|
| 前端 | Next.js 14 (React + TypeScript), Tailwind CSS | SPA 式内部管理界面，nginx 提供静态资源 + `/api` 反向代理 |
| 后端 API | FastAPI (Python 3.12), SQLAlchemy 2.x, Pydantic v2 | RESTful API，RBAC 权限控制，HttpOnly cookie 认证 |
| 数据库 | PostgreSQL 16 + pgvector | 业务数据 + 可选向量检索（LLM 匹配） |
| 缓存/消息 | Redis 7 | Celery broker + result backend |
| 异步任务 | Celery | PDF 生成、哈希计算、LLM 匹配（Phase 2+） |
| 部署 | Docker Compose | 5 个服务，一键启动 |

详见 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## 3. 环境要求 (Environment Requirements)

| 依赖 | 版本 | 说明 |
|---|---|---|
| Docker Desktop | 最新版 (含 Docker Engine + Compose v2) | Windows/macOS/Linux 均可 |
| Python | 3.12 (Docker 内置) | 主机编辑可用 3.13+，运行以容器为准 |
| Node.js | 20 (Docker 内置) | 前端构建在容器内完成 |
| PostgreSQL | 16 + pgvector (Docker 镜像) | 无需主机安装 |
| Redis | 7 (Docker 镜像) | 无需主机安装 |

**无需在主机安装 Python/Node/PostgreSQL**——所有运行时依赖均在 Docker 容器内。主机仅需 Docker Desktop。

---

## 4. Windows + Docker Desktop 快速启动 (Quick Start)

### 4.1 克隆并配置环境变量

```powershell
git clone <repo-url> maggie
cd maggie
copy .env.example .env
```

编辑 `.env`，至少修改 `APP_SECRET` 为一个随机字符串（64 字符）。

### 4.2 构建并启动所有服务

```powershell
docker compose up --build
```

首次构建约 5-10 分钟（需下载 Playwright Chromium ~300MB）。启动后：

| 服务 | 地址 | 说明 |
|---|---|---|
| 前端 | http://localhost:3000 | 登录页面 |
| API | http://localhost:8000 | FastAPI |
| API 文档 | http://localhost:8000/api/docs | Swagger UI |
| 健康检查 | http://localhost:8000/health | `{"status":"ok"}` |

### 4.3 后台启动（开发模式）

```powershell
docker compose up -d postgres redis
docker compose up -d api worker frontend
```

---

## 5. 环境变量 (Environment Variables)

完整配置见 `.env.example`：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_ENV` | `development` | `production` 时启用 Secure cookie |
| `APP_SECRET` | `change-me-...` | JWT 签名密钥，**生产必须修改** |
| `DATABASE_URL` | `postgresql://maggie:maggie@postgres:5432/maggie` | 数据库连接串 |
| `REDIS_URL` | `redis://redis:6379/0` | Redis 连接串 |
| `FILE_STORAGE_ROOT` | `/data/archive` | 文件存储根目录（Docker volume） |
| `MAX_UPLOAD_SIZE_MB` | `100` | 上传文件大小上限 |
| `DEFAULT_TIMEZONE` | `Asia/Taipei` | 默认时区 |
| `DEFAULT_CURRENCY` | `TWD` | 默认币别 |
| `LLM_ENABLED` | `false` | 是否启用 LLM 匹配（Phase 2+） |
| `LLM_PROVIDER` | `openai-compatible` | LLM 提供商 |
| `LLM_BASE_URL` | (空) | LLM API 地址 |
| `LLM_API_KEY` | (空) | LLM API 密钥 |
| `LLM_MODEL` | (空) | LLM 模型名称 |
| `EMBEDDING_MODEL` | (空) | 向量嵌入模型 |

---

## 6. 数据库迁移 (Database Migration)

Alembic 管理 schema 迁移，共 14 个版本（Phase 1 + Phase 2）：

| 迁移 | 内容 | 阶段 |
|---|---|---|
| 001 | 身份模型：organizations, users, roles, user_roles | Phase 1 |
| 002 | 项目模型：companies, projects, project_members, project_parties | Phase 1 |
| 003 | 合同模型：contracts, contract_versions, contract_items, payment_rules | Phase 1 |
| 004 | 文档模型：storage_roots, documents, document_links | Phase 1 |
| 005 | 请款模型：payment_applications, lines, retention_entries, milestone_events | Phase 1 |
| 006 | 审批模型：approval_workflows, approval_steps, approvals, audit_logs | Phase 1 |
| 007 | 标准项目：standard_items, standard_item_aliases, standard_cost_versions | Phase 2 |
| 008 | 变更单：variations, variation_lines | Phase 2 |
| 009 | 扣款：deductions | Phase 2 |
| 010 | 发票：invoices, invoice_application_links | Phase 2 |
| 011 | 收款：collections, collection_allocations | Phase 2 |
| 012 | 财务调整：financial_adjustments | Phase 2 |
| 013 | 项目映射：item_mappings, mapping_components | Phase 2 |
| 014 | 匹配审核：matching_reviews | Phase 2 |

**运行迁移：**

```powershell
docker compose run --rm api alembic upgrade head
```

**回滚一个版本：**

```powershell
docker compose run --rm api alembic downgrade -1
```

**查看当前版本：**

```powershell
docker compose run --rm api alembic current
```

---

## 7. 初始管理员创建 (Initial Admin Creation)

```powershell
docker compose run --rm api python scripts/init_admin.py
```

默认创建：

| 字段 | 值 |
|---|---|
| 邮箱 | `admin@maggie.local` |
| 密码 | `admin123` |
| 组织 | MAGGIE (Maggie Construction) |
| 角色 | `SYSTEM_ADMIN` |

**生产环境必须立即修改密码。**

---

## 8. 示例数据导入 (Sample Data Import)

系统内置两套已知事实种子数据，用于验证核心流程：

| 项目 | 合同 | 说明 |
|---|---|---|
| 25-032 | CQ880A-11501 | 2 个合同版本、6 项明细、3 期请款（含保留款释放 980,496）、2 笔扣款（71,000）、3 张发票、2 笔收款（差异 90/30） |
| 24-023 | FS11308001 | 38,980,000 含税总价、树状明细（4+ 父项）、多单位（处/式/孔/m/m³） |

**导入：**

```powershell
docker compose run --rm api python scripts/seed.py
```

导入后可用 `admin@maggie.local / admin123` 登录查看。

---

## 9. 文件存储目录 (File Storage)

文件存储在 Docker volume `archive`，映射到容器内 `/data/archive`：

```
/data/archive/
  {organization_code}/
    {internal_project_code}/
      contracts/{external_contract_no}/v001/{original,extracted}/
      applications/{application_no}/{attachments,generated}/
      variations/ deductions/ milestones/ invoices/ collections/
      correspondence/ reports/
```

- 原始文件 `is_immutable=true`，永不覆盖。
- 上传时计算 SHA-256 哈希，重复哈希标记但不合并业务链接。
- 下载通过 `document_id` 流式返回，绝不暴露服务器绝对路径。

**查看存储卷：**

```powershell
docker volume inspect maggie_archive
```

---

## 10. 测试命令 (Test Commands)

### 后端单元 + 集成测试

```powershell
docker compose run --rm api python -m pytest tests/ -v
```

Phase 1 + Phase 2 预期 50 项测试通过（19 项规格测试 + 31 项单元测试）：

| # | 测试 | 层级 | 阶段 |
|---|---|---|---|
| 1 | 合同项目合计 | calc_engine unit | Phase 1 |
| 2 | 版本不覆盖 | service + db | Phase 1 |
| 3 | 超量拦截 | calc_engine | Phase 1 |
| 4 | 未批准变更不可请款 | service | Phase 2 |
| 5 | 保留款计算 | calc_engine | Phase 1 |
| 6 | 项目级保留款例外 | service | Phase 2 |
| 7 | 保留款释放 | service + ledger | Phase 1 |
| 8 | 税额与舍入 | calc_engine | Phase 1 |
| 9 | 扣款税务处理 | service | Phase 2 |
| 10 | 过账幂等 | api | Phase 1 |
| 11 | 已过账不可编辑 | api | Phase 1 |
| 12 | 发票/收款差异 | service | Phase 2 |
| 13 | 路径穿越防护 | file_service | Phase 1 |
| 14 | 文件哈希 | file_service | Phase 1 |
| 15 | 项目权限隔离 | api + rbac | Phase 1 |
| 16 | LLM 关闭核心流程 | integration | Phase 1 |
| 17 | LLM 输出 schema | matching (stub + fixture) | Phase 2 |
| 18 | 跨项目数据隔离 | api | Phase 2 |
| 19 | PDF 合计一致 | docgen + api | Phase 1 |

### 前端测试（Phase 2+）

```powershell
cd frontend
npm test
```

---

## 11. 备份与恢复 (Backup / Restore)

### 数据库备份

```powershell
docker compose exec postgres pg_dump -U maggie maggie > backup_$(Get-Date -Format yyyyMMdd).sql
```

### 数据库恢复

```powershell
Get-Content backup_20260722.sql | docker compose exec -T postgres psql -U maggie maggie
```

### 文件存储备份

```powershell
docker run --rm -v maggie_archive:/data -v ${PWD}:/backup alpine tar czf /backup/archive_backup.tar.gz -C /data .
```

### 文件存储恢复

```powershell
docker run --rm -v maggie_archive:/data -v ${PWD}:/backup alpine tar xzf /backup/archive_backup.tar.gz -C /data
```

**建议**：每日自动备份 DB + 文件卷，保留 30 天滚动副本。

---

## 12. LLM 启用/禁用 (LLM Enable/Disable)

LLM 匹配为**可选功能**，不影响核心请款/计算/审批/文档流程。

### 禁用（默认）

`.env` 中设置：

```
LLM_ENABLED=false
```

所有匹配走别名 + 规则 + 全文检索（+ 向量，如 pgvector 可用）。

### 启用（Phase 2+）

```
LLM_ENABLED=true
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
```

LLM 仅从系统提供的候选中排序并解释，**不能**创建标准项目 ID、计算成本、决定转换、自动审批或写入数据库。所有 LLM 输出需人工审核。

---

## 13. 参考文件导入 (Reference File Import — Phase 3)

真实合同/邮件/PDF 文件通过 `scripts/import_reference.py` 导入（Phase 3 实现）：

```powershell
# 1. 将文件放入参考文件目录
# 2. 运行导入器（OCR + 项目识别 → 人工审核队列）
docker compose run --rm api python scripts/import_reference.py --dir /path/to/reference/files
```

导入流程：文件上传 → OCR 提取（Phase 3）→ 项目自动识别 → 进入人工审核队列。Phase 1 使用已知事实种子数据，不含真实文件。

---

## 14. 已知限制 (Known Limitations — Phase 3 待实现)

Phase 1 + Phase 2 已实现核心请款闭环 + 计费与发票收款 + 标准项目匹配，以下功能在 Phase 3 完成：

| 功能 | Phase | 状态 | 说明 |
|---|---|---|---|
| OCR 文字识别 | 3 | 待实现 | 合同原件 OCR 提取 |
| LLM 语义匹配 | 2 | ✅ 已实现 | 标准项目智能映射（Stub + OpenAI 兼容） |
| 变更单 (Variations) | 2 | ✅ 已实现 | 合同变更全额台账 |
| 保留款完整台账 | 2 | ✅ 已实现 | HOLD/RELEASE/ADJUSTMENT/REVERSAL 完整分类账 |
| 扣款完整台账 | 2 | ✅ 已实现 | 多类型扣款 + 税务处理 |
| 发票与收款 | 2 | ✅ 已实现 | 发票登记、收款分配、差异核销 |
| 标准项目映射 | 2 | ✅ 已实现 | 别名、规则、全文、向量、LLM 匹配 |
| 报表 (11 种) | 3 | 待实现 | DB 视图 + 导出器 |
| 数据库视图 (8 个) | 3 | 待实现 | 性能优化索引 |
| 备份一致性检查 | 3 | 待实现 | 自动化验证 |
| E2E 测试 | 3 | 待实现 | Playwright 全流程 |

---

## 15. 生产部署注意事项 (Production Notes)

### 安全

- **HTTPS**：使用反向代理（nginx/Caddy/ALB）终止 TLS，设置 `APP_ENV=production` 启用 Secure cookie。
- **密钥**：`APP_SECRET` 必须为 64 字符随机字符串；`LLM_API_KEY` 通过环境变量注入，不写入代码或日志。
- **CORS**：生产环境将 `allow_origins` 限定为实际域名。
- **数据库密码**：修改默认 `maggie/maggie` 凭据。

### 资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2'
  worker:
    deploy:
      resources:
        limits:
          memory: 2G
  postgres:
    deploy:
      resources:
        limits:
          memory: 1G
```

### 其他

- 定期备份（见 §11）。
- 监控 Celery worker 队列积压。
- Playwright Chromium 占用 ~300MB，确保 worker 容器有足够内存。
- 审计日志为追加只读，定期归档。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md) — 系统架构与服务说明
- [BUSINESS_RULES.md](BUSINESS_RULES.md) — 业务流程与规则
- [SECURITY.md](SECURITY.md) — 安全设计与 RBAC

## 默认账号

| 角色 | 邮箱 | 密码 |
|---|---|---|
| 系统管理员 | `admin@maggie.local` | `admin123` |

> ⚠️ 生产环境必须修改默认密码。
