# 安全设计 (Security)

## 概述

Maggie 遵循最小权限、纵深防御原则。所有敏感操作需认证 + 授权 + 审计。本文档涵盖 RBAC、认证、文件安全、审计日志等安全机制。

---

## 1. RBAC 角色与权限 (Role-Based Access Control)

### 9 个系统角色

| 角色 | 说明 | 典型权限 |
|---|---|---|
| `SYSTEM_ADMIN` | 系统管理员 | 全局管理，绕过项目成员检查 |
| `CONTRACT_ADMIN` | 合同管理员 | 合同录入、版本审批 |
| `PROJECT_USER` | 项目用户 | 查看所属项目、创建请款 |
| `PROJECT_MANAGER` | 项目负责人 | 项目级审批（请款第一步） |
| `COST_REVIEWER` | 造价审核 | 合同明细审核、造价确认 |
| `FINANCE_REVIEWER` | 财务复核 | 财务级审批（请款第二步）、过账 |
| `FINANCE_USER` | 财务用户 | 发票登记、收款登记 |
| `AUDITOR` | 审计员 | 只读访问 + 审计日志查看 |
| `VIEWER` | 查看者 | 只读访问 |

### 项目级角色 (`ProjectMemberRoleEnum`)

用户在项目中的角色独立于系统角色：

| 项目角色 | 说明 |
|---|---|
| `PROJECT_MANAGER` | 项目负责人 |
| `COST_REVIEWER` | 造价审核 |
| `PROJECT_USER` | 项目用户 |
| `FINANCE_USER` | 财务用户 |

### 权限检查实现

```python
# 角色检查
def require_role(*allowed_roles: UserRoleEnum):
    async def checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(r in allowed_roles for r in current.roles):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return current
    return checker

# 项目成员检查
async def require_project_member(project_id, current, db):
    if UserRoleEnum.SYSTEM_ADMIN in current.roles:
        return current  # 管理员绕过
    # 查询 project_members 表...
    if not member:
        raise HTTPException(status_code=403, detail="Not a project member")
```

- **URL 不可绕过**：权限检查在服务层执行，前端路由切换无法绕过后端校验。
- `SYSTEM_ADMIN` 绕过项目成员检查，但操作仍记录审计日志。

---

## 2. 认证与 Cookie (Authentication)

### HttpOnly + Secure Cookie

| Cookie | 用途 | 属性 |
|---|---|---|
| `access_token` | API 访问令牌（JWT） | `HttpOnly`, `Secure`(生产), `SameSite=Lax`, 15 分钟 |
| `refresh_token` | 刷新令牌 | `HttpOnly`, `Secure`(生产), `SameSite=Lax`, `Path=/api/auth`, 7 天 |
| `csrf_token` | CSRF 防护 | `Secure`(生产), `SameSite=Lax`, 7 天（非 HttpOnly，前端需读取） |

```python
response.set_cookie(
    "access_token", access_token,
    max_age=15 * 60,
    httponly=True, secure=(APP_ENV == "production"), samesite="lax",
)
```

- **HttpOnly**：JavaScript 无法读取 token，防 XSS 窃取。
- **Secure**（生产）：仅 HTTPS 传输。
- **SameSite=Lax**：防 CSRF 跨站提交。
- **短期 access + 长期 refresh**：access 15 分钟过期，refresh 7 天，降低泄露风险。

### 密码哈希

- 使用 Argon2 算法（`argon2-cffi`）。
- **绝不存储明文密码**。
- 密码永不出现在日志中。

### JWT 令牌

- Access token：`{sub: user_id, type: "access"}`，15 分钟过期。
- Refresh token：`{sub: user_id, type: "refresh"}`，7 天过期。
- 签名密钥 `APP_SECRET` 通过环境变量注入。

---

## 3. CSRF 防护 (Cross-Site Request Forgery)

### 双 Token 模式

1. 登录时下发 `csrf_token` cookie（非 HttpOnly，前端可读）。
2. 前端在变更请求（POST/PUT/DELETE）头中携带 `X-CSRF-Token: <csrf_token>`。
3. 后端比对 cookie token 与 header token，不匹配返回 403。

```python
def verify_csrf(request: Request):
    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(status_code=403, detail="CSRF token invalid")
```

---

## 4. 项目级访问控制 (Project-Level Access Control)

- 用户必须存在于 `project_members` 表中（`status=ACTIVE`）才能访问对应项目资源。
- `SYSTEM_ADMIN` 绕过此检查。
- 检查在服务层执行，**非前端路由**——直接调用 API 也无法绕过。
- 跨项目数据隔离由测试 #15（项目权限隔离）和 #18（跨项目数据隔离）验证。

---

## 5. 文件路径穿越防护 (Path Traversal Prevention)

### 路径安全解析

```python
def _resolve_safe_path(storage_root, relative_path) -> Path:
    base = Path(storage_root.base_path).resolve()
    target = (base / relative_path).resolve()
    try:
        target.relative_to(base)  # 确保在根目录内
    except ValueError:
        raise PathTraversalException(f"Path escapes storage root")
    return target
```

- 上传时对 `relative_path` 执行 `resolve()` 规范化，消除 `../` 等遍历。
- 断言解析后路径必须 `is_relative_to(storage_root)`，否则抛 `PathTraversalException`。
- **用户永不输入绝对路径**——DB 仅存 `storage_root_id + relative_path`。
- 由测试 #13（路径穿越）验证。

### 文件类型限制

允许的扩展名：`.pdf`, `.png`, `.jpg`, `.jpeg`, `.xlsx`, `.csv`, `.msg`, `.eml`。

### 大小限制

- `MAX_UPLOAD_SIZE_MB`（默认 100MB）环境变量配置。
- 超限返回 400。

---

## 6. SHA-256 文件哈希 (File Integrity)

- 上传时计算 SHA-256（流式 8KB 分块读取，避免大文件内存溢出）。
- 哈希存储在 `documents.sha256` 字段。
- 重复哈希标记但**不合并**业务链接（每个业务链接独立保留）。
- 确保文件完整性可验证，防篡改。
- 由测试 #14（文件哈希）验证。

```python
def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
```

### 文件不可变性

- 原始文件 `is_immutable=true`，**永不覆盖**。
- 下载通过 `document_id` 流式返回，**绝不暴露服务器绝对路径**。
- 设置 `Content-Disposition: attachment; filename="<original_name>"`（RFC 5987）。
- 逻辑删除设置 `deleted_at`；物理删除为独立管理工具。

---

## 7. 审计日志 (Audit Logging)

### 追加只读

- `audit_logs` 表为**追加只读**——无更新 API，不可通过 UI 编辑。
- 记录所有关键操作：审批、过账、作废、下载、权限变更。

### 记录内容

| 字段 | 说明 |
|---|---|
| `user_id` | 操作人 |
| `action` | 操作类型（APPROVE, POST, VOID, DOWNLOAD 等） |
| `resource_type` | 资源类型 |
| `resource_id` | 资源 ID |
| `timestamp` | 操作时间（TIMESTAMPTZ） |
| `details` | 操作详情（JSON） |

### 日志安全

- **密码、密钥、完整敏感文件内容永不写入日志**。
- 审计日志定期归档，不可篡改。

---

## 8. 安全响应头 (Security Headers)

通过 `SecurityHeadersMiddleware` 注入：

| 头 | 值 | 说明 |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | 防 MIME 类型嗅探 |
| `X-Frame-Options` | `DENY` | 防点击劫持（禁止 iframe 嵌入） |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | 限制 Referrer 泄露 |

```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
```

---

## 9. 速率限制 (Rate Limiting)

### 登录速率限制

- 登录接口限制尝试频率，防暴力破解。
- 建议配置：同一 IP 5 次失败/分钟，锁定 15 分钟。

### 上传速率限制

- 文件上传接口限制频率 + 大小（`MAX_UPLOAD_SIZE_MB`）。

### 实现说明

- Phase 1 通过 FastAPI middleware 实现基础限流。
- 生产环境建议使用 Redis + `slowapi` 或 API 网关（nginx limit_req）。

---

## 10. 密钥管理 (Secret Management)

### 环境变量注入

所有密钥通过环境变量注入，**不硬编码在代码中**：

| 变量 | 说明 |
|---|---|
| `APP_SECRET` | JWT 签名密钥 |
| `DATABASE_URL` | 数据库连接（含密码） |
| `REDIS_URL` | Redis 连接 |
| `LLM_API_KEY` | LLM API 密钥（Phase 2+） |

### 最佳实践

- `.env` 文件**不提交**到版本控制（`.gitignore` 已排除）。
- 生产环境使用 Docker Secrets / Kubernetes Secrets / 云厂商密钥管理服务。
- 密钥轮换：定期更换 `APP_SECRET`，使旧 token 失效。
- **日志永不包含密码、密钥或完整敏感文件内容**。

---

## 11. SQL 注入防护

- 全部使用 SQLAlchemy ORM + 参数化查询，**不拼接 SQL 字符串**。
- 用户输入经 Pydantic 验证后才进入查询。

---

## 12. XSS 防护

- React 默认输出编码，防止 XSS。
- `X-Content-Type-Options: nosniff` 防止 MIME 嗅探。
- 前端不使用 `dangerouslySetInnerHTML`（除非经过严格消毒）。

---

## 13. CORS 配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 生产环境限定实际域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- 开发环境允许 `localhost:3000`。
- **生产环境必须限定为实际域名**。

---

## 安全检查清单

| 项目 | 状态 | 验证测试 |
|---|---|---|
| HttpOnly + Secure cookie | ✅ | — |
| CSRF 双 token | ✅ | — |
| 项目级访问控制 | ✅ | #15, #18 |
| 路径穿越防护 | ✅ | #13 |
| SHA-256 文件哈希 | ✅ | #14 |
| 审计日志追加只读 | ✅ | — |
| 安全响应头 | ✅ | — |
| 密码 Argon2 哈希 | ✅ | — |
| 环境变量密钥管理 | ✅ | — |
| LLM 关闭核心流程可用 | ✅ | #16 |
| 过账幂等 | ✅ | #10 |
| 已过账不可编辑 | ✅ | #11 |
