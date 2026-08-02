# Phase B: Frontend Core Pages Completion

**Date**: 2026-08-03
**Status**: Design approved, ready for implementation plan
**Scope**: B1 (Dashboard) + B2 (File inbox) + B3 (Contract extraction review) + B4 (Master Budget) + B5 (Approval & exception center) + B6 (Reports completion) — all six together

---

## 1. Problem Statement

The Maggie system has completed Phase 1 + 2 + 3 + A (70 passing tests, 16 migrations, Celery + OCR + PDF all working). The backend has 88 API endpoints across 19 routers and 8 DB-view reports, but the frontend has critical gaps against `Prompt.md` §8.2–§8.14:

1. **B1 Dashboard** (`/dashboard`) — shows only 3 StatCards; "pending applications" is hard-coded to 0. Spec 8.2 requires 11 clickable indicators.
2. **B2 File inbox** (spec 8.3) — page does not exist. No UI for upload, OCR status, duplicate detection, or project identification.
3. **B3 Contract extraction review** (spec 8.5) — page does not exist. No left/right side-by-side review of original document vs. extracted fields.
4. **B4 Master Budget** (spec 8.6) — page does not exist. No tree-structured budget vs. actual vs. cost/margin view.
5. **B5 Approval & exception center** (spec 8.10) — page does not exist. No centralized hub for 11 exception types.
6. **B6 Reports** (`/reports`) — sidebar is missing `contract-item-balances` (API exists). Rendering is crude (raw column names, no pagination, inconsistent money formatting). Spec 8.14 requires 11 report types.

The backend APIs and DB views required for these pages are largely in place; the work is primarily frontend, plus three small backend additions to keep business aggregation server-side (RESTRAIN #35).

## 2. Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Phase B scope | All 6 pages in one phase | User chose to do all 6 together; each page is independently deliverable so risk is contained by sequencing |
| B3 extraction source | OCR-assisted manual entry | OCR adapter extracts raw text only; building an LLM extraction pipeline would expand scope into backend/ML. User approved minimal path. |
| B1 metric source | New `GET /api/dashboard/summary` | RESTRAIN #35 forbids client-side business aggregation; one endpoint returns all 11 indicators |
| B5 interaction | Unified list + inline approve/reject buttons | User chose; fewer clicks than link-only, less code than per-type tabs |
| B6 report completion | Only add reports with existing APIs | `contract-item-balances` API exists. Spec-required reports without DB views are shown as "规划中". No new views in this phase. |
| B2 project identification | User manually selects project on upload | Backend has no auto-identification logic; RESTRAIN #30 forbids self-filling uncertain rules. Auto-ID deferred. |
| B4 master-budget data | New `GET /api/projects/{id}/master-budget` | Tree + margin calculation is business logic; must be server-side (RESTRAIN #35) |
| B3 OCR text | Persist to `documents.ocr_text` via migration 017 | `run_ocr` task currently discards text; B3 left panel needs it |
| Frontend testing | No new framework this phase | Introducing Jest/Playwright would expand scope; backend TDD covers business logic; manual verification checklist for UI |

## 3. Architecture

### 3.1 Principles

- **Server-side aggregation**: all business computation stays in FastAPI. Frontend only renders API responses (RESTRAIN #35).
- **No breaking changes**: reuse existing `lib/api.ts`, `hooks/useAuth`, `components/AppShell`, `components/ui/common`. New shared components go in `components/ui/`.
- **Routing**: Next.js 14 App Router conventions. New pages under `frontend/app/`. Sidebar `AppShell.tsx` gets new entries.
- **API proxy**: reuse `next.config.mjs` `/api/*` rewrite. No frontend network-layer changes.
- **RBAC**: all new endpoints use `deps.get_current_user` + project membership checks, matching existing patterns.

### 3.2 Backend Additions

#### 3.2.1 `GET /api/dashboard/summary` (new file `app/api/dashboard.py`)

Returns a single object with all 11 spec 8.2 indicators plus per-project breakdown and recent audit entries. Aggregates from existing DB views + tables, filtered by the current user's accessible projects (via `project_members`).

Response shape:
```json
{
  "total_contract_amount": "decimal",
  "gross_completed_total": "decimal",
  "approved_total": "decimal",
  "invoiced_total": "decimal",
  "collected_total": "decimal",
  "retention_held_total": "decimal",
  "invoice_outstanding_total": "decimal",
  "pending_variations": 0,
  "pending_applications": 0,
  "pending_mappings": 0,
  "overclaim_exceptions": 0,
  "contract_version_diffs": 0,
  "per_project": [
    {"project_id": "uuid", "code": "25-032", "name": "...", "contract_amount": "...", "approved_total": "...", "retention_held": "..."}
  ],
  "recent_audit": [
    {"id": "uuid", "action": "...", "created_at": "iso8601"}
  ]
}
```

Indicator sourcing:
| Indicator | Source |
|---|---|
| total_contract_amount | SUM(active contract versions `amount_inc_tax`) for accessible projects |
| gross_completed_total | SUM(`payment_applications.gross_completed_amount` where status=POSTED) |
| approved_total | SUM(`payment_applications.invoice_amount` where status=POSTED) |
| invoiced_total | SUM(`invoices.amount_inc_tax` where status=ISSUED) |
| collected_total | SUM(`collections.amount_received` where status=RECEIVED) |
| retention_held_total | SUM(`v_retention_balances.balance`) |
| invoice_outstanding_total | SUM(`v_invoice_outstanding.outstanding_amount`) |
| pending_variations | COUNT(`variations` where status=PENDING) |
| pending_applications | COUNT(`payment_applications` where status in (SUBMITTED, PROJECT_APPROVED)) |
| pending_mappings | COUNT(`item_mappings` where status=PENDING_REVIEW) |
| overclaim_exceptions | COUNT(`v_contract_item_balances` where remaining_quantity < 0) |
| contract_version_diffs | COUNT of contracts with >1 version having distinct `amount_inc_tax` |

#### 3.2.2 `GET /api/approvals/pending` (extend `app/api/approvals.py`)

Returns a unified list of pending items across resource types. Each row has a uniform shape so the frontend can render one table:

```json
{
  "items": [
    {
      "resource_type": "variation|payment_application|item_mapping|deduction|matching_review|contract_version|collection_variance",
      "resource_id": "uuid",
      "description": "string",
      "project_id": "uuid",
      "project_code": "25-032",
      "amount": "decimal|null",
      "waiting_for_role": "PROJECT_MANAGER|FINANCE_REVIEWER|CONTRACT_ADMIN|...",
      "created_at": "iso8601",
      "approve_url": "/api/variations/{id}/approve",
      "reject_url": "/api/variations/{id}/reject|null",
      "detail_url": "/projects/{project_id}/variations"
    }
  ]
}
```

Scans:
- `contract_versions` where status=UNDER_REVIEW → waiting_for_role=CONTRACT_ADMIN
- `variations` where status=PENDING → waiting_for_role=PROJECT_MANAGER (or CONTRACT_ADMIN)
- `item_mappings` where status=PENDING_REVIEW → waiting_for_role=COST_REVIEWER
- `payment_applications` where status=SUBMITTED → resource_type=`payment_application_pm` → waiting_for_role=PROJECT_MANAGER
- `payment_applications` where status=PROJECT_APPROVED → resource_type=`payment_application_finance` → waiting_for_role=FINANCE_REVIEWER
- `deductions` where status=PENDING → waiting_for_role=FINANCE_REVIEWER
- `matching_reviews` where status=PENDING → waiting_for_role=COST_REVIEWER (covers 标准项目匹配审核 + 提前释放保留款审批, since retention early-release flows through matching_reviews per existing schema)
- `retention_entries` where entry_type=RELEASE and status=PENDING (if such status exists; otherwise skip — see note below) → waiting_for_role=FINANCE_REVIEWER
- `v_collection_variances` where variance ≠ 0 → resource_type=`collection_variance` → waiting_for_role=FINANCE_USER (no approve URL, only detail)
- `v_contract_item_balances` where remaining_quantity < 0 → resource_type=`overclaim` → waiting_for_role=PROJECT_MANAGER (no approve URL; detail → `/projects/{project_id}/budget`)

Note on retention release: the existing `retention_entries` model uses an entry_type ledger (HOLD/RELEASE/ADJUSTMENT/REVERSAL) without an explicit approval status. Early-release approval is modeled via `matching_reviews` (review_type=RETENTION_RELEASE). If implementation finds `retention_entries` has no PENDING status, the retention_entries scan is skipped and only the matching_reviews path is used. This avoids inventing a status field that doesn't exist.

Filters: `?project_id=`, `?resource_type=`, `?waiting_for_role=`. RBAC: only items in user's accessible projects.

#### 3.2.3 `GET /api/projects/{project_id}/master-budget` (new file `app/api/master_budget.py`)

Returns tree-structured rows for the project's active contract version, with all spec 8.6 columns pre-computed:

```json
{
  "contract_id": "uuid",
  "contract_version_id": "uuid",
  "rows": [
    {
      "contract_item_id": "uuid",
      "parent_item_id": "uuid|null",
      "line_no": "1",
      "description": "...",
      "unit": "m",
      "contract_quantity": "100.0000",
      "unit_price": "1000.00",
      "approved_quantity": "100.0000",
      "approved_unit_price": "1000.00",
      "variation_delta": "0.0000",
      "previous_cumulative_quantity": "50.0000",
      "current_period_quantity": "10.0000",
      "cumulative_approved_quantity": "60.0000",
      "remaining_quantity": "40.0000",
      "completed_amount": "60000.00",
      "claimed_amount": "60000.00",
      "retention_balance": "6000.00",
      "invoiced_amount": "50000.00",
      "collected_amount": "45000.00",
      "standard_cost_per_unit": "800.00|null",
      "standard_cost_total": "48000.00|null",
      "expected_margin": "12000.00|null",
      "margin_pct": "20.00|null",
      "exception_status": "none|overclaim|unmapped"
    }
  ]
}
```

Computes margin server-side from `item_mappings` + `standard_cost_versions`. `exception_status`:
- `overclaim` if remaining_quantity < 0
- `unmapped` if no approved `item_mapping` exists for the item
- `none` otherwise

All cumulative/balance/amount fields are read-only on the frontend (spec 8.6 last sentence).

#### 3.2.4 Migration 017 — `documents.ocr_text`

```sql
ALTER TABLE documents ADD COLUMN ocr_text TEXT;
```

`app/tasks/tasks.py` `run_ocr` task: after `adapter.extract()` returns, write `result.text` to `documents.ocr_text` and set `ocr_status=COMPLETED`. On failure, set `ocr_status=FAILED` and leave `ocr_text` null.

`GET /documents/{id}` response includes `ocr_text` (nullable).

#### 3.2.5 `PATCH /api/contracts/contract-versions/{version_id}` (extend `app/api/contracts.py`)

B3 right-panel contract field form needs to update an existing DRAFT/UNDER_REVIEW contract version's header fields (amounts, dates, tax mode). No such endpoint exists today (only POST create + POST approve). Add a minimal PATCH that:

- Accepts a partial body of the editable fields (external_contract_no, contract_name, signed_date, effective_date, currency, tax_mode, tax_rate, original_amount_ex_tax, original_tax_amount, original_amount_inc_tax, change_reason).
- Only allows updates when `version.status in (DRAFT, UNDER_REVIEW)`. Returns 409 otherwise (RESTRAIN #5: no overwriting approved/posted records).
- RBAC: requires CONTRACT_ADMIN role.
- Writes an audit log entry.

This is a small, contained addition needed unambiguously by B3.

### 3.3 Frontend Shared Components

New files in `frontend/components/ui/`:

| Component | File | Purpose |
|---|---|---|
| `Tabs` | `Tabs.tsx` | Reusable tab bar (B3/B4/B5 use). Props: `tabs: {key,label}[]`, `active`, `onChange` |
| `FilterBar` | `FilterBar.tsx` | Top filter row. Props: `filters: {label, options, value, onChange}[]` + `searchValue/onSearchChange` |
| `MoneyCell` | `MoneyCell.tsx` | Right-aligned monospace money `<td>`. Wraps `formatMoney` |
| `DocumentPreview` | `DocumentPreview.tsx` | `<iframe>` for PDF, `<img>` for images. Props: `documentId`. Uses `/api/documents/{id}/preview` |
| `PageLoader` | `PageLoader.tsx` | Skeleton/spinner while loading |
| `ErrorBanner` | `ErrorBanner.tsx` | Red error banner with message + dismiss |
| `ConfirmDialog` | `ConfirmDialog.tsx` | Modal confirm for high-risk actions (RESTRAIN #31). Props: `title`, `message`, `onConfirm`, `onCancel` |

### 3.4 Type & API Layer Extensions

`frontend/lib/types.ts` adds:
- `DashboardSummary` (matches §3.2.1 response)
- `PendingApproval` (matches §3.2.2 item)
- `MasterBudgetRow` (matches §3.2.3 row)
- `FileInboxItem` (document + ocr_status + ocr_text fields)
- `ContractVersionDraft` (form shape for B3)

`frontend/lib/api.ts` adds typed helpers:
- `api.getDashboardSummary()`
- `api.getPendingApprovals(filters)`
- `api.getMasterBudget(projectId)`
- `api.approveResource(url)`, `api.rejectResource(url)` (generic POST to provided URL)

### 3.5 Sidebar Navigation Updates

`frontend/components/AppShell.tsx` `navItems` array adds:
- `{ href: '/inbox', label: '文件收件箱', icon: '...' }`
- `{ href: '/approvals', label: '审批中心', icon: '...' }`

Master Budget is a tab inside `/projects/[id]`, not a sidebar entry.

---

## 4. Page Designs

### 4.1 B1 — Dashboard (`/dashboard`)

Refactor existing `frontend/app/dashboard/page.tsx`:

**Layout**:
1. **Top stat grid**: 4-column × 3-row grid of 12 StatCards (11 spec indicators + "项目数"). Each card clickable → navigates to corresponding detail:
   - 合同总金额 → `/reports?report=project-summary`
   - 待审核请款 → `/approvals?resource_type=payment_application`
   - 超合同数量异常 → `/approvals?resource_type=overclaim` (or `/reports?report=contract-item-balances&filter=overclaim`)
   - etc.
2. **Project list table** (preserve existing): add columns 合同总金额, 累计请款, 未释放保留款 (from `summary.per_project`).
3. **Recent audit log**: bottom card showing latest 5 entries from `summary.recent_audit`.

**Data**: single `api.getDashboardSummary()` call on mount.

### 4.2 B2 — File Inbox (`/inbox`)

New file `frontend/app/inbox/page.tsx`:

**Layout**:
1. **FilterBar**: project dropdown + document_type dropdown + ocr_status multi-select + search input.
2. **Upload zone**: drag-drop area + "选择文件" button. On upload, require project selection (dropdown modal). Calls `POST /api/documents/upload` with `project_id`, `document_type`. On success, OCR task auto-submits (Celery `run_ocr` already wired). Toast shows "上传成功，OCR 处理中".
3. **File list table**: columns 原文件名 / 项目 / 类型 / 大小 / SHA-256前8位 / OCR状态 / 置信度 / 上传时间 / 操作.
   - OCR status badge: PENDING (灰), RUNNING (蓝+spinner), COMPLETED (绿), FAILED (红), N/A (灰).
   - Operations: 预览 (opens `DocumentPreview` modal), 下载 (calls `/documents/{id}/download`), 重新识别 (re-submits OCR task, only if status=FAILED or N/A).
4. **OCR polling**: rows with `ocr_status in (PENDING, RUNNING)` trigger `setInterval` every 3s calling `GET /documents?project_id=...` to refresh. Exponential backoff to 15s cap. Stops when no rows pending.

**Project identification**: manual selection only (§2 decision). No auto-ID. Filename never used for project assignment (RESTRAIN #2).

### 4.3 B3 — Contract Extraction Review (`/contracts/[id]/extract`)

New file `frontend/app/contracts/[id]/extract/page.tsx`. Entry point: "合同" tab in `/projects/[id]` shows "抽取审核" button on contract rows that have a version with status=UNDER_REVIEW or DRAFT.

**Layout** (left/right side-by-side, spec 8.5):
- **Left panel (40%)**:
  - `DocumentPreview` for the contract version's `source_document_id`.
  - Collapsible "OCR 原文" panel below, showing `documents.ocr_text` (from `GET /documents/{id}`). Empty state if no OCR text.
- **Right panel (60%)**:
  - **Contract field form**: external_contract_no, contract_name, signed_date, effective_date, currency, tax_mode (EXCLUSIVE/INCLUSIVE/MIXED), tax_rate, original_amount_ex_tax, original_tax_amount, original_amount_inc_tax. Fields pre-filled from existing contract version data (editable). Save → `PATCH /api/contracts/contract-versions/{vid}` (§3.2.5). Only allowed when version status is DRAFT or UNDER_REVIEW; otherwise form is read-only.
  - **Contract items table**: editable rows. Columns: line_no, item_code, source_description, unit, contract_quantity, unit_price, line_amount (auto-calc = qty×price, read-only), calculation_method (dropdown), tax_category, retention_applicable (checkbox). Add row / delete row buttons. Save → `POST /contract-versions/{vid}/items`.
  - **Validation bar** (bottom of right panel): shows 合计校验 (sum of line_amount == amount_ex_tax) and 税额校验 (amount_ex_tax × tax_rate == tax_amount, within rounding tolerance). Red text blocks submit if failed.
  - **Action bar**: "保存草稿" (status stays DRAFT), "提交审核" (status → UNDER_REVIEW), "批准" (status → APPROVED, calls `/contracts/{id}/versions/{vid}/approve`, only CONTRACT_ADMIN+ role). All actions use `ConfirmDialog`.

**OCR text persistence**: depends on migration 017 + `run_ocr` task update (§3.2.4).

### 4.4 B4 — Master Budget (`/projects/[id]/budget`)

New tab in `/projects/[id]` page (11th tab, key=`budget`). New file `frontend/app/projects/[id]/budget/page.tsx`.

**Layout**:
- **Contract selector**: dropdown of project's contracts (default active_version's contract). Changing reloads data.
- **Tree table**: single large table with indented rows showing `contract_items` hierarchy (indent by `parent_item_id` depth). All 16 columns from §3.2.3 response. Sticky header. Horizontal scroll for wide columns.
- **Column groups** (visual grouping via header backgrounds):
  - 合同基准: line_no, description, unit, contract_quantity, unit_price
  - 变更: variation_delta
  - 累计: previous_cumulative, current_period, cumulative_approved, remaining
  - 金额: completed_amount, claimed_amount, retention_balance, invoiced, collected
  - 成本毛利: standard_cost_per_unit, standard_cost_total, expected_margin, margin_pct
  - 状态: exception_status (badge: 超量=红, 未映射=灰, 正常=绿)
- **Footer totals row**: sum of numeric columns.
- **Read-only**: all cells non-editable (spec 8.6). "维护标准成本" link → `/projects/[id]/catalog`.

**Data**: `api.getMasterBudget(projectId)` (single call). Contract selector filters client-side from a cached full-project response, or reloads via `?contract_id=` query param on the endpoint.

### 4.5 B5 — Approval & Exception Center (`/approvals`)

New file `frontend/app/approvals/page.tsx`:

**Layout**:
1. **FilterBar**: resource_type dropdown covering spec 8.10's 11 exception types, mapped to the scan sources in §3.2.2:
   - 合同版本审批 → `contract_version`
   - 项目映射审批 → `item_mapping`
   - 请款审批 → `payment_application_pm` + `payment_application_finance` (split by stage in the scan)
   - 变更审批 → `variation`
   - 超量异常 → `overclaim`
   - 单价变化 → folded into `overclaim` (surfaces when remaining_quantity < 0 due to price-driven amount) — same scan, presented with description noting "单价变化"
   - 前期累计差异 → folded into `payment_application` validation failures; surfaced as `payment_application` rows with description noting "前期累计差异"
   - 提前释放保留款 → `matching_review` (review_type=RETENTION_RELEASE)
   - 扣款审批 → `deduction`
   - 发票及收款差异 → `collection_variance`
   - 作废和冲销 → folded into `matching_review` / `retention` REVERSAL entries; surfaced as `matching_review` rows with description noting "作废/冲销"
   The dropdown presents all 11 spec type labels; selecting one filters by the underlying `resource_type`(s) per the mapping above. + project dropdown + waiting_for_role dropdown + search.
2. **Unified table**: 类型 (badge) / 描述 / 项目 / 金额 / 等待角色 / 创建时间 / 操作.
   - Operations column: inline buttons.
     - "批准" (green) — calls `api.approveResource(item.approve_url)`. Disabled if current user's roles don't include `waiting_for_role`. Opens `ConfirmDialog` first.
     - "拒绝" (red) — calls `api.rejectResource(item.reject_url)` if `reject_url` not null. Same gating. Opens `ConfirmDialog` with required reason input.
     - "查看" (gray) — navigates to `item.detail_url`.
   - On approve/reject success: remove row from list + toast "已批准/已拒绝". On error: `ErrorBanner` + keep row.
3. **Empty state**: "暂无待处理事项" with icon.
4. **Pagination**: 50 per page, frontend pagination.

**Data**: `api.getPendingApprovals(filters)` with filter params. Refetch on filter change. No polling (manual refresh button in header).

### 4.6 B6 — Reports (`/reports`) Completion

Refactor existing `frontend/app/reports/page.tsx`:

1. **Sidebar list**: add `contract-item-balances` (8th report, API exists). Also list spec 8.14 reports without views: 项目合同总览, 请款历史, 应收账龄 — clicking shows "规划中" `EmptyState` card explaining "待后端视图实现（Phase C+）".
2. **Rendering enhancements**:
   - **Money columns**: expand `isMoney` column-name match list. Right-align + `formatMoney` (thousands separator, 2 decimals).
   - **Status columns**: use `StatusBadge` for any column named `status` / `*_status`.
   - **UUID columns**: detect names ending in `_id`; display first 8 chars + full value in `title` tooltip.
   - **Date columns**: detect `*_date` / `*_at` / `created_at`; format as `YYYY-MM-DD HH:mm`.
   - **Null values**: display `—` (em dash).
   - **Long text**: truncate at 50 chars with ellipsis + tooltip.
3. **`contract-item-balances` specific**: add contract dropdown filter at top (calls `?contract_id=`). Highlight rows where `remaining_quantity < 0` in red.
4. **Pagination**: 50 rows per page, with prev/next + page number. Frontend pagination (full dataset fetched, sliced client-side — datasets are small for internal tool).
5. **Export button** (optional, time permitting): "导出 CSV" button per report — client-side CSV generation from current rows. Not required by spec; include only if time allows.

---

## 5. Testing Strategy

### 5.1 Backend Tests (pytest, TDD)

New test files in `backend/tests/`:

| File | Coverage |
|---|---|
| `test_dashboard_summary.py` | `/api/dashboard/summary` returns all 11 indicators; per_project breakdown; RBAC filters to user's projects; empty state when no projects |
| `test_approvals_pending.py` | `/api/approvals/pending` aggregates all 7 resource types; filters by project/type/role; `approve_url`/`reject_url`/`detail_url` correct; project isolation |
| `test_master_budget.py` | `/api/projects/{id}/master-budget` tree structure; margin calculation; `exception_status` (overclaim/unmapped/none); read-only response shape; project isolation |
| `test_ocr_text_persist.py` | `run_ocr` task writes `ocr_text` + sets `ocr_status=COMPLETED`; on failure sets FAILED + null text; `GET /documents/{id}` includes `ocr_text` |
| `test_contract_version_patch.py` | `PATCH /api/contracts/contract-versions/{vid}` updates DRAFT/UNDER_REVIEW fields; returns 409 for APPROVED/SUPERSEDED; RBAC requires CONTRACT_ADMIN; audit log written |
| `test_migration_017.py` | migration applies cleanly; `ocr_text` column nullable; rollback works |

All tests written first (red), then implementation (green).

### 5.2 Regression Gate

Existing 70 tests must remain green:
```powershell
docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/ -v
```

### 5.3 Frontend Verification (manual checklist)

No new frontend test framework (§2 decision). Manual checklist in spec:
1. Login as admin → dashboard shows 12 stat cards with non-zero values for seed data.
2. Click each stat card → navigates to correct page/filter.
3. `/inbox` → upload a file → OCR status transitions PENDING→RUNNING→COMPLETED.
4. `/contracts/[id]/extract` → left panel shows PDF, right panel form editable, validation blocks inconsistent totals, approve creates APPROVED version.
5. `/projects/[id]/budget` → tree table renders, totals row correct, overclaim row red, unmapped row gray.
6. `/approvals` → filter by type, approve a variation (row removes), reject a mapping (row removes with reason).
7. `/reports` → all 8 reports render, money right-aligned, status badges, pagination works, contract-item-balances filter by contract.
8. Sidebar shows new 文件收件箱 + 审批中心 entries.

### 5.4 Linting / Typecheck

- Backend: `ruff check backend/` (if configured).
- Frontend: `npm run lint` + `npm run build` (or `tsc --noEmit`) must pass.

---

## 6. Acceptance Criteria (spec alignment)

| Page | spec ref | Acceptance point |
|---|---|---|
| B1 | 8.2 | 11 indicators present + clickable into detail; project table has contract/approved/retention columns; recent audit shown |
| B2 | 8.3 | Upload / preview / download / OCR status / duplicate hash detection (existing backend) / confidence shown / pending-classification queue (manual project select) |
| B3 | 8.5 | Left-right side-by-side; editable fields; source page (OCR text); amount total validation; approve creates APPROVED version |
| B4 | 8.6 | Tree hierarchy; 16 columns; cumulative/balance non-editable; exception status (overclaim/unmapped) |
| B5 | 8.10 | 11 exception types centralized; approve/reject has confirm + role check + audit log (audit via existing approve endpoints) |
| B6 | 8.14 | sidebar 8 reports present; money right-aligned thousands; status badges; pagination; missing reports shown as 规划中 |

---

## 7. Out of Scope (deferred)

| Item | Reason | Next phase |
|---|---|---|
| Auto project identification on file upload | No backend logic; RESTRAIN #30 | Phase C+ |
| LLM structured contract field extraction | User chose OCR-assisted manual entry | Optional, later |
| Spec 8.14 reports without DB views (项目合同总览, 请款历史, 应收账龄) | No backing views; would require backend work | Phase C+ |
| Frontend unit/E2E test framework (Jest/Playwright) | Avoid scope expansion this phase | Phase C |
| Master Budget inline standard-cost editing | spec 8.6 is read-only view | Existing `/projects/[id]/catalog` already maintains cost |
| CSV/Excel export from reports | Nice-to-have, not spec-required | If time permits, else Phase C |
| WebSocket/SSE for OCR + approval real-time updates | Polling sufficient for internal tool volume | Phase C+ |

---

## 8. Implementation Order (to be refined by writing-plans)

1. **Backend** (TDD, 6 tasks): migration 017 + `run_ocr` update → `dashboard.py` → `approvals/pending` → `master_budget.py` → OCR text in `GET /documents/{id}` → `PATCH /contract-versions/{vid}`.
2. **Shared components** (7 components): Tabs, FilterBar, MoneyCell, DocumentPreview, PageLoader, ErrorBanner, ConfirmDialog.
3. **B6 Reports** (no new backend, fastest win to validate pipeline).
4. **B1 Dashboard** (depends on 1).
5. **B4 Master Budget** (depends on 1).
6. **B2 File inbox** (depends on 1 OCR text persist).
7. **B3 Contract extraction** (depends on B2 + DocumentPreview).
8. **B5 Approval center** (depends on 1).
9. **Sidebar nav update + full regression** (70 existing + new tests green).

Each page is independently shippable; if time pressure, B6→B1→B4 deliver visible value early.

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Large scope (6 pages + 3 backend endpoints + migration) | Each page independently deliverable; B6 ships first to validate the pipeline; backend TDD catches regressions early |
| 3 new backend endpoints may introduce regressions | TDD + 70-test green gate before each page merge |
| Migration 017 on `documents` table | Additive `ALTER TABLE ADD COLUMN ocr_text TEXT` (nullable); no data backfill; tested rollback |
| B3 needs a backend PATCH endpoint for DRAFT version field updates | Added as §3.2.5 (definite scope, not conditional). Only updates DRAFT/UNDER_REVIEW versions; 409 otherwise. Small, contained. |
| No frontend test framework → UI bugs slip through | Manual verification checklist (§5.3) executed before declaring page done; backend tests cover all business logic |
| Polling on inbox may cause load | Exponential backoff (3s→15s cap); stops when no pending rows; single project-scoped query per poll |

---

## 10. References

- `Prompt.md` §8.2 (Dashboard), §8.3 (File inbox), §8.5 (Contract extraction), §8.6 (Master Budget), §8.10 (Approval center), §8.14 (Reports)
- `Prompt.md` RESTRAIN #2 (no filename-based project ID), #30 (no self-filling uncertain rules), #31 (high-risk ops need confirm+RBAC+audit), #35 (no client-side business calc)
- `memory.md` §6 Phase B plan
- Existing specs: `docs/superpowers/specs/2026-07-23-phase-a-celery-pdf-ocr-design.md` (Phase A precedes this)
- Backend API surface: 88 endpoints across 19 routers (confirmed via grep)
- DB views (migration 015): 8 views backing `/api/reports/*`
