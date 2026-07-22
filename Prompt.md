ROLE

你是一名资深企业级软件架构师、全栈开发负责人、数据库设计师、工程合约计价顾问和质量保证工程师。你熟悉工程项目合同、报价清单、分期请款、保留款、合同变更、扣款、发票、收款核销、内部标准成本及人工审批流程。

你的任务不是只提供概念设计或页面原型，而是构建一套可实际运行、可审计、可扩展的企业内部“工程合同及请款管理系统”。

工作原则：

1. 先理解业务规则，再设计数据库和界面。
2. 所有金额计算必须确定、可追踪、可复算。
3. 原始合同文字和原件永远保留，不因标准化处理而被替换。
4. LLM只能提供语义匹配建议，不能负责财务计算或最终审批。
5. 已批准的历史记录不得被后续操作静默覆盖。
6. 所有关键数字必须能追溯到合同版本、请款记录、审批记录及原始文件。
7. 默认界面语言为简体中文，代码、数据库字段和API使用清晰一致的英文命名。
8. 面向财务人员、项目经理、工务人员、成本人员、审核人员和系统管理员设计，避免要求普通用户理解技术术语。


REQUEST

请在当前开发环境中设计并实现一套完整的工程合同、标准成本、分期请款、文件归档、审批、发票及收款管理系统。

不要停留在架构说明或静态页面。完成可运行的前端、后端、数据库迁移、文件存储、权限、测试、示例数据、PDF生成和部署说明。

一、建议技术架构

在没有现有技术栈限制时，采用以下架构：

- 前端：React + TypeScript，优先使用Next.js或当前环境中已有的稳定React框架。
- 后端：Python FastAPI。
- ORM：SQLAlchemy。
- 数据库迁移：Alembic。
- 数据库：PostgreSQL。
- 可选语义检索：PostgreSQL pgvector；不可用时退回全文检索和规则匹配。
- 后台任务：Redis + Celery，处理OCR、文档生成、文件哈希和LLM匹配。
- 文件存储：服务器本地文件夹或网络共享文件夹，数据库只保存存储根目录、相对路径、元数据和哈希值。
- PDF生成：HTML模板加无头Chromium打印为PDF。
- Excel输出：使用可维护的Excel模板生成。
- 容器化：Docker Compose，至少包含frontend、api、worker、postgres和redis。
- API文档：OpenAPI。
- 测试：后端单元及集成测试、前端关键组件测试、端到端测试。
- 所有依赖使用当前环境支持的稳定版本并锁定版本，不要盲目使用未经验证的最新版本。

如当前环境已有成熟技术栈，应优先兼容现有项目，但必须保持下述业务模型和验收标准。

二、系统主要业务模式

系统以“网页直接填报请款”为主要模式：

1. 公司先建立项目。
2. 上传并登记合同、报价单及相关原件。
3. 抽取或人工输入合同项目、数量、单位、单价和付款条件。
4. 人工核对后批准一个合同版本，形成Master Budget。
5. 将合同项目映射到公司内部标准项目。
6. 用户建立本期请款申请。
7. 用户选择对应合同项目并输入本期完成数量、完成比例或里程碑状态。
8. 系统自动计算本期金额、累计金额、保留款、税额、扣款及剩余余额。
9. 经过项目审核和财务审核。
10. 系统锁定并过账该期请款。
11. 根据客户模板生成可打印的正式请款单PDF及Excel。
12. 后续登记发票和实际收款，并处理差异。

同时保留“导入历史文件”辅助模式，用于：

- 导入旧合同及旧请款资料。
- 导入客户退回或修改后的文件。
- 对历史项目补建数据库。
- OCR提取扫描件。
- 将提取结果放入人工审核，不直接过账。

三、项目识别

一个项目可能同时存在：

- 公司内部项目编号，例如`25-032`。
- 业主或总包合同编号，例如`CQ880A-11501`。
- 工程名称。
- 业主、总包、分包或供应商。
- 签约日期。
- 合同总金额。

系统不得仅根据文件名判断项目。

项目识别应综合以上字段。发现以下情况时必须进入“待确认项目”队列：

- 内部项目编号相同，但合同编号不同。
- 合同编号相同，但工程名称或公司不同。
- 文件中没有明确项目编号。
- 同一文件似乎包含多个项目。
- OCR置信度过低。
- 文件与目标项目的合同金额差异过大。

四、数据库设计

所有主要业务表必须包含：

- 主键，优先UUID。
- `organization_id`。
- 创建人、创建时间。
- 更新人、更新时间。
- 逻辑删除字段或状态字段。
- 必要的版本号或乐观锁字段。
- 必要的唯一约束、外键和检查约束。

金额使用`DECIMAL(18,2)`或等价精确类型。

工程数量使用`DECIMAL(18,4)`。

比例使用精确小数类型，不使用二进制浮点数。

时间使用含时区时间戳。

4.1 组织、用户和权限

实现以下数据表：

1. `organizations`

   - `id`
   - `code`
   - `name`
   - `default_currency`
   - `default_timezone`
   - `status`

2. `users`

   - `id`
   - `organization_id`
   - `email`
   - `display_name`
   - `department`
   - `password_hash`或外部身份ID
   - `status`
   - `last_login_at`

3. `roles`

   至少包含：

   - SYSTEM_ADMIN
   - CONTRACT_ADMIN
   - PROJECT_USER
   - PROJECT_MANAGER
   - COST_REVIEWER
   - FINANCE_REVIEWER
   - FINANCE_USER
   - AUDITOR
   - VIEWER

4. `user_roles`

5. `project_members`

   控制用户可访问哪些项目及其项目内角色。

6. `companies`

   保存业主、总包商、分包商、供应商和本公司资料。

7. `project_parties`

   保存公司在项目中的角色及生效日期。

实现项目级权限隔离。普通用户不能通过修改URL访问无权限项目。

4.2 项目及合同

1. `projects`

   至少包含：

   - `internal_project_code`
   - `project_name`
   - `description`
   - `project_manager_id`
   - `start_date`
   - `planned_end_date`
   - `actual_end_date`
   - `status`
   - `currency`
   - `default_tax_rate`

2. `contracts`

   至少包含：

   - `project_id`
   - `external_contract_no`
   - `contract_name`
   - `customer_company_id`
   - `contractor_company_id`
   - `signed_date`
   - `effective_date`
   - `currency`
   - `tax_mode`：EXCLUSIVE、INCLUSIVE或MIXED
   - `tax_rate`
   - `original_amount_ex_tax`
   - `original_tax_amount`
   - `original_amount_inc_tax`
   - `status`
   - `active_version_id`

3. `contract_versions`

   每次合同基准变化必须建立新版本，不覆盖旧版本。

   字段至少包含：

   - `contract_id`
   - `version_no`
   - `version_type`：QUOTATION、SIGNED_CONTRACT、PROVISIONAL、INTERNAL_ADJUSTMENT、APPROVED_VARIATION
   - `effective_date`
   - `amount_ex_tax`
   - `tax_amount`
   - `amount_inc_tax`
   - `status`：DRAFT、UNDER_REVIEW、APPROVED、SUPERSEDED、REJECTED
   - `change_reason`
   - `source_document_id`
   - `approved_by`
   - `approved_at`

4. `contract_items`

   必须支持树状层级。

   字段至少包含：

   - `contract_version_id`
   - `parent_item_id`
   - `line_no`
   - `item_code`
   - `source_description`
   - `normalized_description`
   - `unit`
   - `contract_quantity`
   - `unit_price`
   - `line_amount`
   - `calculation_method`
   - `tax_category`
   - `retention_applicable`
   - `retention_exempt_reason`
   - `is_heading`
   - `is_billable`
   - `sort_order`
   - `source_page`
   - `source_bbox_json`
   - `extraction_confidence`

   `calculation_method`至少支持：

   - QUANTITY：数量乘单价。
   - LUMP_SUM：一式或直接金额。
   - PERCENTAGE：按比例计价。
   - MILESTONE：里程碑计价。
   - ALLOWANCE：暂列金额。
   - ADJUSTMENT：扣款或调整。
   - HEADING：标题或汇总行，不直接计价。

5. `payment_rules`

   不得把80/10/10、20%保留款等规则硬编码在程序中。

   字段至少包含：

   - `contract_version_id`
   - `contract_item_id`，允许为空，表示合同级规则
   - `rule_type`
   - `rule_name`
   - `rate`
   - `condition_code`
   - `condition_description`
   - `calculation_base`
   - `release_sequence`
   - `effective_from`
   - `effective_to`
   - `is_active`

   `rule_type`至少支持：

   - PROGRESS_PAYMENT
   - RETENTION_HOLD
   - RETENTION_RELEASE
   - MILESTONE_PAYMENT
   - ADVANCE_PAYMENT
   - DEDUCTION
   - TAX
   - ROUNDING
   - PENALTY

6. `variations`及`variation_lines`

   变更必须支持：

   - 新增项目。
   - 删除项目。
   - 数量增减。
   - 单价变化。
   - 项目之间金额重新分配。
   - 待审批变更。
   - 正式批准变更。
   - 被拒绝变更。

   未批准变更不得增加可请款上限。

4.3 内部标准项目及成本

1. `standard_items`

   字段至少包含：

   - `standard_code`
   - `canonical_name`
   - `category`
   - `subcategory`
   - `standard_unit`
   - `description`
   - `scope_included`
   - `scope_excluded`
   - `status`

2. `standard_item_aliases`

   保存已经人工批准的同义词及客户常用名称。

3. `standard_cost_versions`

   字段至少包含：

   - `standard_item_id`
   - `effective_from`
   - `effective_to`
   - `labor_cost`
   - `material_cost`
   - `equipment_cost`
   - `subcontract_cost`
   - `overhead_cost`
   - `total_unit_cost`
   - `currency`
   - `region`
   - `cost_source`
   - `approved_by`
   - `approved_at`

4. `item_mappings`

   保存合同项目到标准项目的映射。

   字段至少包含：

   - `contract_item_id`
   - `mapping_type`：ONE_TO_ONE、ONE_TO_MANY、MANY_TO_ONE、NOT_COMPARABLE
   - `status`：SUGGESTED、PENDING_REVIEW、APPROVED、REJECTED、NEEDS_CLARIFICATION
   - `match_method`：EXACT_ALIAS、RULE、FULL_TEXT、VECTOR、LLM、MANUAL
   - `confidence`
   - `unit_compatibility`
   - `conversion_required`
   - `llm_explanation`
   - `review_comment`
   - `approved_by`
   - `approved_at`

5. `mapping_components`

   支持一个合同项目拆分为多个标准成本项目。

   字段至少包含：

   - `item_mapping_id`
   - `standard_item_id`
   - `allocation_method`
   - `allocation_rate`
   - `conversion_formula`
   - `conversion_factor`
   - `effective_quantity`
   - `approved_by`

任何换算系数、拆分比例及成本金额必须由人工确认，不得由LLM自行决定。

4.4 请款

1. `payment_applications`

   字段至少包含：

   - `project_id`
   - `contract_id`
   - `contract_version_id`
   - `application_no`
   - `period_no`
   - `period_start`
   - `period_end`
   - `application_date`
   - `status`
   - `currency`
   - `gross_completed_amount`
   - `retention_held_amount`
   - `retention_released_amount`
   - `deduction_amount`
   - `taxable_amount`
   - `tax_amount`
   - `invoice_amount`
   - `approved_amount`
   - `revision_no`
   - `supersedes_application_id`
   - `posted_at`

   状态至少包括：

   - DRAFT
   - VALIDATING
   - NEEDS_CHANGES
   - SUBMITTED
   - PROJECT_APPROVED
   - FINANCE_APPROVED
   - POSTED
   - GENERATED
   - SENT
   - REJECTED
   - CANCELLED
   - SUPERSEDED

2. `payment_application_lines`

   字段至少包含：

   - `payment_application_id`
   - `contract_item_id`
   - `contract_version_id`
   - `description_snapshot`
   - `unit_snapshot`
   - `unit_price_snapshot`
   - `previous_approved_quantity`
   - `current_claimed_quantity`
   - `current_approved_quantity`
   - `cumulative_approved_quantity`
   - `current_completed_amount`
   - `retention_rate`
   - `retention_held`
   - `retention_released`
   - `deduction_amount`
   - `taxable_amount`
   - `tax_amount`
   - `net_amount`
   - `calculation_method`
   - `user_explanation`
   - `validation_status`

   必须保存描述、单位及单价快照，避免后续合同版本变化导致历史请款重算。

3. `milestone_events`

   保存：

   - 试验合格。
   - 立坑完成。
   - 正式验收。
   - 保固期结束。
   - 其他合同里程碑。

4. `retention_entries`

   使用账本方式保存：

   - HOLD
   - RELEASE
   - ADJUSTMENT
   - REVERSAL

   不要只保存一个可任意修改的保留款余额。

5. `deductions`

   类型至少支持：

   - ADVANCE_PAYMENT_OFFSET
   - MATERIAL_DEDUCTION
   - EQUIPMENT_DEDUCTION
   - PENALTY
   - BACK_CHARGE
   - QUALITY_DEDUCTION
   - TAX_ADJUSTMENT
   - ROUNDING
   - OTHER

   每笔扣款必须保存：

   - 原因。
   - 未税金额。
   - 税务处理。
   - 相关公司。
   - 支持文件。
   - 审批记录。

6. `approval_workflows`、`approval_steps`及`approvals`

   支持按金额、项目、合同或异常类型配置审批流程。

   审批至少包括：

   - 合同版本审批。
   - 标准项目映射审批。
   - 变更审批。
   - 项目负责人请款审批。
   - 财务请款审批。
   - 保留款提前释放审批。
   - 扣款审批。
   - 作废及冲销审批。

4.5 发票和收款

1. `invoices`

   保存：

   - 发票号码。
   - 发票日期。
   - 未税金额。
   - 税额。
   - 含税金额。
   - 发票状态。
   - 客户。
   - 电子发票或扫描件。
   - 作废或折让状态。

2. `invoice_application_links`

   支持：

   - 一张发票对应多期请款。
   - 一期请款拆成多张发票。

3. `collections`

   保存：

   - 收款日期。
   - 实际收款金额。
   - 银行交易编号。
   - 付款公司。
   - 付款方式。
   - 汇款证明文件。

4. `collection_allocations`

   支持一笔收款分配给多张发票。

5. `financial_adjustments`

   处理：

   - 银行手续费。
   - 短款。
   - 多付款。
   - 退款。
   - 折让。
   - 汇率差异。
   - 人工核销差异。

4.6 文件存储

实现以下数据表：

1. `storage_roots`

   字段至少包含：

   - `code`
   - `base_path`
   - `storage_type`
   - `is_active`
   - `read_only`
   - `health_status`

2. `documents`

   字段至少包含：

   - `project_id`
   - `storage_root_id`
   - `original_name`
   - `stored_name`
   - `relative_path`
   - `document_type`
   - `mime_type`
   - `file_extension`
   - `size_bytes`
   - `sha256`
   - `version_no`
   - `is_original`
   - `is_generated`
   - `is_immutable`
   - `uploaded_by`
   - `uploaded_at`
   - `ocr_status`
   - `extraction_status`
   - `retention_status`

3. `document_links`

   允许文件关联到：

   - 项目。
   - 合同。
   - 合同版本。
   - 合同项目。
   - 请款。
   - 请款明细。
   - 变更。
   - 扣款。
   - 里程碑。
   - 发票。
   - 收款。
   - 审批记录。

4. `document_templates`

   保存不同客户及不同生效日期的：

   - 请款单模板。
   - 明细表模板。
   - 保留款表模板。
   - 扣款表模板。
   - 发票申请模板。
   - Excel模板。
   - PDF打印模板。

5. `generated_documents`

   保存：

   - 对应请款。
   - 模板版本。
   - 生成时间。
   - 生成文件。
   - 生成参数快照。
   - 版本号。
   - 是否最终版。

五、文件夹存储规则

使用环境变量配置：

```text
FILE_STORAGE_ROOT=[例如 D:\BillingArchive 或容器中的 /data/archive]
```

数据库不得直接信任用户输入的绝对路径。

数据库主要保存`storage_root_id + relative_path`。

建议目录：

```text
{FILE_STORAGE_ROOT}/
  {organization_code}/
    {internal_project_code}/
      contracts/
        {external_contract_no}/
          v001/
            original/
            extracted/
      applications/
        {application_no}/
          attachments/
          generated/
      variations/
      deductions/
      milestones/
      invoices/
      collections/
      correspondence/
      reports/
```

具体要求：

1. 上传后的原件为只读，不能被覆盖。
2. 同名文件使用UUID作为实际文件名。
3. 原始名称保存在数据库。
4. 所有文件计算SHA-256。
5. 使用哈希检测重复文件，但不得因为哈希相同而错误合并不同项目的业务关联。
6. 下载时使用数据库中的原始文件名。
7. 用户不得获得服务器真实绝对路径。
8. 后端提供安全的预览和下载API。
9. 解析前必须标准化路径并确认最终路径仍位于配置的存储根目录内，防止目录穿越。
10. 限制文件大小、扩展名和MIME类型。
11. 为病毒扫描保留接口。
12. 删除业务记录时默认只逻辑删除文件索引，不直接删除原件。
13. 数据库和文件目录提供一致性检查工具。
14. 提供备份和恢复说明，明确数据库和文件目录必须作为同一备份周期处理。

六、核心计算规则

实现一个独立、可单元测试的计算引擎。

不得将关键计算散落在前端组件中。

6.1 数量型项目

```text
本期完成金额
= 本期批准数量 × 当前请款适用的合同单价快照
```

用户输入本期数量，金额只读。

6.2 一式项目

允许输入：

- 本期完成比例，或
- 本期直接金额。

直接金额必须填写原因，并可配置为必须人工审批。

6.3 里程碑项目

只有关联的里程碑状态达到批准条件后才可请款。

6.4 数量上限

```text
可用合同数量
= 当前有效合同数量
+ 已批准变更数量
- 已批准减项数量

剩余数量
= 可用合同数量
- 累计批准请款数量
```

超出时阻止过账，并生成变更或异常申请。

6.5 保留款

```text
本期保留款
= 适用保留款的本期计价基础 × 保留比例
```

必须支持：

- 合同级保留款。
- 项目级例外。
- 部分项目不扣保留款。
- 分阶段释放。
- 条件性释放。
- 人工批准的提前释放。
- 冲销和更正。

保留款释放使用独立账本记录，不要删除原来的保留记录。

6.6 扣款和税额

扣款必须具有税务分类。

税额根据客户及合同的舍入规则计算。

实现可配置的舍入策略，不得在代码中假设所有客户都采用同一种舍入方式。

6.7 请款净额

系统内部至少分开显示：

- 本期完成金额。
- 本期保留款。
- 本期释放保留款。
- 本期扣款。
- 本期未税可开票金额。
- 税额。
- 含税发票金额。
- 实际收款金额。

6.8 不得直接保存一个可以随意修改的“剩余余额”

通过数据库视图或查询服务计算：

```text
剩余合同数量
未完成合同金额
完成但尚未请款金额
批准但尚未开票金额
未释放保留款
已开票未收款
收款差异
```

七、LLM项目匹配

LLM不是核心系统运行的强制依赖。未配置LLM时，请款、计算、审批和文件生成仍必须正常工作。

匹配流程：

1. 清理全角半角、空格、繁简体差异、括号及常见单位写法。
2. 查找已经批准的精确别名。
3. 使用规则和全文搜索筛选候选。
4. 可选使用向量检索获得候选。
5. LLM只能从系统提供的候选标准项目中进行排序和解释。
6. LLM结果进入人工转换审批。
7. 人工批准后写入别名及映射数据库。

LLM结构化输出必须通过JSON Schema验证，至少包含：

```json
{
  "source_item_id": "uuid",
  "candidate_matches": [
    {
      "standard_item_id": "uuid",
      "confidence": 0.0,
      "reasoning": "简短可审计的匹配原因",
      "unit_compatibility": "SAME|CONVERTIBLE|INCOMPATIBLE|UNKNOWN",
      "conversion_required": false,
      "scope_differences": [],
      "questions_for_reviewer": []
    }
  ],
  "suggested_mapping_type": "ONE_TO_ONE|ONE_TO_MANY|MANY_TO_ONE|NOT_COMPARABLE"
}
```

限制：

- LLM不得创建不存在的标准项目ID。
- LLM不得生成成本。
- LLM不得决定换算系数。
- LLM不得自动批准映射。
- LLM不得执行数据库写入。
- 合同项目文字视为不可信输入，不得允许其中的指令影响系统提示词或工具调用。
- LLM调用失败时必须退回人工审批流程。

只有“已经人工批准的精确别名且单位完全一致”才可以配置为自动采用。

以下情况必须人工审批：

- 第一次出现的映射。
- 单位不一致。
- 一对多或多对一。
- 需要换算。
- 一式项目。
- 项目范围不清楚。
- 毛利异常。
- LLM或向量匹配。
- 新建标准项目。

八、网页功能

实现响应式桌面优先界面，默认简体中文。

8.1 登录及权限

- 登录。
- 登出。
- 修改密码。
- 当前用户及角色。
- 无权限页面返回明确提示。
- 管理员维护用户、角色及项目权限。

8.2 管理驾驶舱

显示：

- 合同总金额。
- 累计完成金额。
- 累计批准请款。
- 已开票。
- 已收款。
- 未释放保留款。
- 已开票未收款。
- 待批准变更。
- 待审核请款。
- 待审核标准项目映射。
- 超合同数量异常。
- 合同金额版本差异。

所有指标可点击进入对应明细。

8.3 文件收件箱

- 上传PDF、图片、Excel、CSV和邮件文件。
- 选择或自动识别项目。
- 显示文件类型、OCR状态、重复检测和识别置信度。
- 无法识别时进入待人工分类。
- 支持预览和下载。
- 上传操作写入审计日志。

8.4 项目列表及项目详情

项目详情使用标签页展示：

- 项目概况。
- 合同版本。
- Master Budget。
- 标准项目映射。
- 请款。
- 变更。
- 保留款。
- 扣款。
- 发票。
- 收款。
- 文件。
- 审计记录。

8.5 合同抽取及审核

左右并排：

- 左侧显示原始PDF或图片。
- 右侧显示抽取字段和合同项目。
- 可修改识别错误。
- 显示来源页码和位置。
- 验证项目金额合计。
- 验证未税、税额和含税金额。
- 确认付款及保留款规则。
- 审核通过后建立批准合同版本。

8.6 Master Budget

显示：

- 项目层级。
- 合同原始数量和单价。
- 当前批准数量和单价。
- 已批准变更。
- 前期累计数量。
- 本期数量。
- 累计批准数量。
- 剩余数量。
- 已完成金额。
- 已请款金额。
- 保留款余额。
- 已开票。
- 已收款。
- 内部标准成本。
- 预计毛利。
- 异常状态。

不得允许用户直接修改累计和余额字段。

8.7 标准项目目录

- 搜索及分类。
- 标准项目维护。
- 别名维护。
- 成本版本维护。
- 成本批准。
- 历史映射查看。
- 禁用项目但保留历史引用。

8.8 项目转换审批

左侧：

- 合同原始描述。
- 单位、数量和单价。
- 上下层项目。
- 原文件截图。
- 备注和施工范围。

中间：

- 匹配候选。
- 置信度。
- 单位兼容性。
- 范围差异。
- 历史匹配记录。
- LLM解释。

右侧允许：

- 批准建议。
- 更换标准项目。
- 拆分成多个标准项目。
- 合并映射。
- 定义换算。
- 标记不可比较。
- 新建标准项目申请。
- 要求补充说明。
- 设为仅当前项目有效。
- 设为公司通用别名。

8.9 请款填报

步骤式界面：

1. 选择项目和有效合同。
2. 新建期别。
3. 输入计价区间。
4. 选择合同项目。
5. 输入本期数量、比例或里程碑。
6. 上传证明文件。
7. 系统计算。
8. 显示前期、本期、累计及余额。
9. 显示验证结果。
10. 提交审批。

数量型项目不得直接修改系统计算金额。

8.10 审批与异常中心

集中处理：

- 合同版本审批。
- 项目映射审批。
- 请款审批。
- 变更审批。
- 超量异常。
- 单价变化。
- 前期累计差异。
- 提前释放保留款。
- 扣款审批。
- 发票及收款差异。
- 作废和冲销。

8.11 变更、保留款及扣款

分别提供账本视图，不允许只显示最终余额。

8.12 发票及收款

支持：

- 根据已批准请款建立发票申请。
- 一期多票及一票多期。
- 登记发票号码。
- 登记实际收款。
- 自动计算未收金额。
- 人工核销小额差异。
- 显示应收账龄。

8.13 文件档案库

- 按项目、合同、请款和文件类型浏览。
- 在线预览PDF及图片。
- 下载时恢复原始文件名。
- 显示文件哈希和版本。
- 显示关联业务记录。
- 显示上传人和下载记录。

8.14 报表

至少包含：

- 项目合同总览。
- Master Budget。
- 请款历史。
- 保留款余额。
- 变更汇总。
- 扣款汇总。
- 发票及收款对账。
- 应收账龄。
- 合同售价和内部标准成本比较。
- 毛利分析。
- 异常清单。

九、正式请款单生成

系统应支持客户级模板。

每个模板必须有版本号和生效日期。

请款单至少包含：

- 公司名称。
- 业主。
- 工程名称。
- 合同编号。
- 请款日期。
- 请款期数。
- 合同总价。
- 项次。
- 项目名称。
- 单位。
- 合同数量。
- 单价。
- 复价。
- 前期累计数量及金额。
- 本期数量及金额。
- 本期累计数量及金额。
- 施工金额。
- 保留款。
- 计价金额。
- 税额。
- 发票金额。
- 实领或预计实领金额。
- 备注。
- 签核空白栏位。

生成要求：

1. 输出可打印PDF。
2. 可选输出Excel。
3. 使用批准数据生成。
4. 在生成记录中保存所有输入参数快照。
5. 重新生成必须建立新版本。
6. 已发送版本不可被同名覆盖。
7. 不得自动复制原合同中的印章或签名。
8. 印章、电子签名及发送客户必须作为独立受控功能，默认不启用。
9. 版面应适合A4打印。
10. 数字列右对齐，千分位清晰。
11. 分页时重复表头。
12. 不允许项目行被不合理截断。
13. PDF与数据库合计必须一致。

十、审核和过账规则

提交请款时执行：

- 合同版本是否有效。
- 项目是否可计价。
- 本期数量是否为负。
- 累计数量是否超过可用合同数量。
- 单价是否等于适用合同版本单价。
- 前期累计是否与已过账数据一致。
- 保留款规则是否正确。
- 税额是否正确。
- 扣款是否有审批。
- 里程碑是否满足。
- 相关证明文件是否齐全。
- 是否存在未批准变更。
- 是否存在重复期别。

请款过账必须具有幂等性。同一个批准动作重复提交，不得产生两次账本记录。

已过账请款不得直接编辑。

更正方式：

- 建立冲销记录。
- 或建立修订版并指向被替代版本。
- 保留原记录、审批和生成文件。

十一、API

提供清晰REST API或等价接口，至少覆盖：

- `/auth`
- `/users`
- `/roles`
- `/companies`
- `/projects`
- `/projects/{id}/members`
- `/contracts`
- `/contracts/{id}/versions`
- `/contract-versions/{id}/items`
- `/payment-rules`
- `/standard-items`
- `/standard-item-aliases`
- `/item-mappings`
- `/mapping-reviews`
- `/variations`
- `/payment-applications`
- `/payment-applications/{id}/lines`
- `/payment-applications/{id}/validate`
- `/payment-applications/{id}/submit`
- `/payment-applications/{id}/approve`
- `/payment-applications/{id}/post`
- `/payment-applications/{id}/generate`
- `/retention-entries`
- `/deductions`
- `/invoices`
- `/collections`
- `/documents`
- `/documents/{id}/preview`
- `/documents/{id}/download`
- `/approvals`
- `/reports`

API必须包含：

- 权限验证。
- 输入验证。
- 分页。
- 筛选。
- 排序。
- 统一错误结构。
- 操作审计。
- 并发及版本冲突处理。

十二、审计及安全

实现：

- RBAC。
- 项目级访问控制。
- 密码安全散列。
- HttpOnly及Secure Cookie，或安全的短期访问令牌机制。
- CSRF防护。
- 登录限速。
- 上传限速及大小限制。
- 文件类型验证。
- 防止路径穿越。
- 防止SQL注入。
- 防止XSS。
- 安全响应头。
- 敏感配置使用环境变量。
- 日志不得写入密码、密钥或完整敏感文件内容。
- 所有审批、过账、作废、下载和权限修改写入审计日志。
- 审计日志不得通过普通界面修改。
- 提供数据导出及备份方案。

十三、数据库视图或查询模型

至少实现：

- `v_contract_item_balances`
- `v_project_commercial_summary`
- `v_retention_balances`
- `v_uninvoiced_approved_amounts`
- `v_invoice_outstanding`
- `v_collection_variances`
- `v_cost_margin_analysis`
- `v_pending_exceptions`

十四、开发顺序

按以下顺序实施，不要同时创建大量空页面：

第一阶段：核心闭环

1. 基础项目和身份权限。
2. PostgreSQL数据库及迁移。
3. 文件存储及下载。
4. 项目、合同版本和合同项目。
5. Master Budget。
6. 网页直接填报请款。
7. 计算引擎。
8. 项目及财务审批。
9. 过账。
10. PDF请款单生成。

第二阶段：扩展业务

1. 标准项目目录。
2. 项目映射及人工审批。
3. LLM可选匹配。
4. 变更管理。
5. 保留款及扣款账本。
6. 发票及收款。

第三阶段：完善

1. 历史文件导入。
2. OCR接口。
3. 客户模板管理。
4. 报表。
5. 备份恢复。
6. 完整端到端测试。
7. 性能和安全检查。

每个阶段必须产生可运行、可验证的结果，不要只创建路由、空组件或“稍后实现”按钮。


RESOURCE

一、参考文件

如果当前环境可以访问，请将以下文件复制或挂载到：

```text
[REFERENCE_FILES_DIR]
```

参考文件包括：

1. `(开发票) 25-032 远扬北捷CQ880A污水工作井地改.msg`
2. `24-023计价.pdf`
3. `25-032 第二期计价表 用印完成 2026-04-28.pdf`
4. `25-032 第三期 ( 请领试验完成10%保留款) 2026-07-16.pdf`
5. `25-032扣款单据.pdf`
6. `2024-09-19 合约双方用印完成(24-023).pdf`
7. `2025-01-20 第四期请款单(MD+微型桩+MI保留款)24-023.pdf`
8. `2026-01-13 第一期请款(25-032)(第一期).csv`
9. `2026-04-27 合约双方用印完成(25-032).pdf`

这些文件可能属于不同项目，禁止混合数据。

二、已知项目事实

25-032：

- 内部项目编号：25-032。
- 外部合同编号：CQ880A-11501。
- 工程：污水工作井地盘改良工程。
- 原始签约报价税前金额：10,476,190。
- 含税金额：11,000,000。
- 原合同包含六个主要项目。
- 第一版签约报价项目金额为：

```text
2,494,000
661,200
5,980,000
455,000
850,000
35,990
合计 10,476,190
```

后续请款表出现另一合同基准：

```text
2,489,485
660,003
6,021,860
458,185
850,000
35,990
合计 10,515,523
```

两种基准差额为39,333。系统必须把它表现为两个合同版本或待确认调整，不能覆盖原始签约版。

第二期请款参考数据：

```text
本期施工金额：401,792
本期保留款：74,600
本期未税计价金额：327,192
税额：16,360
含税发票金额：343,552
```

第三期参考数据：

```text
本期新增施工金额：0
释放保留款：980,496
税额：49,025
含税发票金额：1,029,521
```

扣款参考：

```text
60,000 + 11,000 = 71,000，未税
```

邮件中的开票参考：

```text
前期发票未税金额：7,843,966
本期业主允许请领未税金额：1,971,024
剩余未发票金额：661,200
7,843,966 + 1,971,024 + 661,200 = 10,476,190

本期扣款：71,000
本次建议开票未税金额：
1,971,024 - 71,000 = 1,900,024
```

该邮件金额与第三期请款单并非完全相同，系统必须产生差异提示，不得自行假定缺失业务依据。

历史收款差异示例：

```text
发票金额 7,892,613，实际收款 7,892,523，差异 90
发票金额 343,552，实际收款 343,522，差异 30
```

系统不得自动认定差异原因，应要求财务选择手续费、短款、折让或其他原因。

24-023：

- 内部项目编号：24-023。
- 外部合同编号：FS11308001。
- 含税合同总价：38,980,000。
- 包含多个工程组及大量子项目。
- 用于测试树状合同项目、多单位、累计数量、保留款及复杂请款。
- 24-023的数据不得进入25-032的余额、请款或成本计算。

三、运行配置占位符

提供`.env.example`，至少包含：

```text
APP_ENV=development
APP_SECRET=[请生成安全随机值]
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
FILE_STORAGE_ROOT=/data/archive
MAX_UPLOAD_SIZE_MB=100
DEFAULT_TIMEZONE=Asia/Taipei
DEFAULT_CURRENCY=TWD

LLM_ENABLED=false
LLM_PROVIDER=[openai-compatible-or-other]
LLM_BASE_URL=[optional]
LLM_API_KEY=[optional]
LLM_MODEL=[optional]
EMBEDDING_MODEL=[optional]
```

LLM未配置时系统必须正常运行。

四、缺少参考文件时

如果参考文件不可访问：

1. 不要伪造文件内容或声称已经读取。
2. 根据上述已知事实建立经过标识的示例数据。
3. 将真实文件导入功能保留为可配置模块。
4. 在README中说明如何把文件放入`[REFERENCE_FILES_DIR]`并执行导入。
5. 不得因为缺少样本文件而停止实现核心系统。


RESTRAIN

1. 不得把24-023和25-032合并为同一项目。
2. 不得根据文件名直接确定项目归属。
3. 不得覆盖原始合同文件。
4. 不得覆盖历史合同版本。
5. 不得覆盖已过账请款。
6. 不得直接修改累计数量、余额或保留款余额。
7. 不得使用浮点数计算财务金额。
8. 不得把合同付款规则硬编码为固定80/10/10或固定20%。
9. 不得假设所有合同税率、舍入方式和保留款规则相同。
10. 不得让LLM计算金额、成本、税额、保留款或余额。
11. 不得让LLM自行批准项目映射。
12. 不得让LLM自行创建换算系数。
13. 不得把标准项目名称替换原始合同项目名称。
14. 不得将LLM建议写成已经确认的事实。
15. 不得把未批准变更加入可请款余额。
16. 不得把扣款自动当成合同减项。
17. 不得把请款、发票和收款视为同一状态。
18. 不得将发票金额和实际收款差异静默抹平。
19. 不得把服务器绝对文件路径发送给前端用户。
20. 不得接受可能逃离存储根目录的文件路径。
21. 不得自动嵌入合同中的印章、签名或个人签字。
22. 不得自动发送客户邮件、自动开票或自动执行付款。
23. 不得使用真实客户数据调用外部LLM，除非用户明确配置并授权。
24. 不得把密码、密钥、完整文件内容或敏感个人资料写入普通日志。
25. 不得只提供静态HTML、设计图、伪代码或空壳页面。
26. 不得用硬编码示例代替数据库持久化。
27. 不得创建点击后无功能的按钮。
28. 不得声称测试通过，除非实际执行过对应测试。
29. 不得删除、移动或修改参考原件。
30. 不确定的业务规则必须配置为待人工确认，而不是自行补全。
31. 所有高风险操作必须有明确确认、权限检查和审计记录。
32. 优先完成可运行核心闭环，不要为未来功能牺牲当前系统的正确性。
33. 保持代码模块化，计算引擎、文件服务、LLM服务、审批服务和文档生成服务必须分离。
34. 保持API与数据库字段命名一致。
35. 不要在前端重复实现后端业务计算。
36. 对任何来自PDF、CSV、邮件或用户输入的文本，都视为不可信数据并进行验证。
37. 不要在缺乏证明时把合同版本差异自动认定为正式变更。
38. 不要把“完成金额”“批准请款”“开票金额”“实际收款”混为一个字段。
39. 生成的请款文件必须来自已批准或明确标识为草稿的数据。
40. 草稿文件必须带有明显“草稿”标识；最终文件不得带草稿标识。


RESULT

最终必须交付一个可以在本地或测试服务器运行的完整项目，并满足以下要求。

一、项目文件

至少包括：

```text
README.md
ARCHITECTURE.md
BUSINESS_RULES.md
SECURITY.md
BACKUP_RESTORE.md
API.md
docker-compose.yml
.env.example
frontend/
backend/
worker/
migrations/
tests/
templates/
sample-data/
scripts/
```

二、README

README必须说明：

1. 系统用途。
2. 技术架构。
3. 环境要求。
4. Windows及Docker Desktop运行方式。
5. 环境变量。
6. 数据库迁移。
7. 初始管理员创建方式。
8. 示例数据导入。
9. 文件存储目录。
10. 测试命令。
11. 备份恢复。
12. LLM启用及禁用方式。
13. 参考文件导入方式。
14. 已知限制。
15. 生产部署注意事项。

三、数据库

必须提供：

- 完整迁移文件。
- 外键、唯一约束及检查约束。
- 必要索引。
- 示例数据。
- 数据库视图。
- 数据库关系图，使用Mermaid或等价格式。
- 数据字典。

四、系统图

在`ARCHITECTURE.md`中提供系统架构图，至少体现：

```mermaid
flowchart LR
    U["网页用户"] --> W["Web前端"]
    W --> API["后端API与权限控制"]

    API --> PM["项目与合同管理"]
    API --> PE["请款计算引擎"]
    API --> WF["审批与异常工作流"]
    API --> FM["发票与收款管理"]
    API --> DM["文件管理服务"]
    API --> MAP["标准项目匹配服务"]

    MAP --> RULE["别名与规则匹配"]
    MAP --> LLM["可选LLM语义建议"]
    MAP --> HR["人工转换审批"]

    PM --> DB[("PostgreSQL")]
    PE --> DB
    WF --> DB
    FM --> DB
    MAP --> DB
    DM --> DB

    DM --> FS["原件及生成文件夹"]
    PE --> GEN["请款单生成器"]
    GEN --> TMP["客户模板库"]
    GEN --> FS
```

五、操作流程图

在`BUSINESS_RULES.md`中提供完整操作流程，至少体现：

```mermaid
flowchart TD
    A["建立项目"] --> B["上传合同原件"]
    B --> C["抽取或人工输入合同资料"]
    C --> D["核对合同项目、单价和付款规则"]
    D --> E{"审核通过？"}

    E -- "否" --> C
    E -- "是" --> F["批准合同版本"]
    F --> G["建立标准项目映射"]
    G --> H{"已有批准规则？"}

    H -- "是" --> I["采用既有映射"]
    H -- "否" --> J["规则、语义及LLM推荐"]
    J --> K["人工转换审批"]
    K --> I

    I --> L["建立Master Budget"]
    L --> M["新建本期请款"]
    M --> N["选择合同项目"]
    N --> O["输入数量、比例或里程碑"]
    O --> P["计算金额、税额、保留款和余额"]
    P --> Q{"存在异常？"}

    Q -- "是" --> R["变更或异常审批"]
    R --> P
    Q -- "否" --> S["项目负责人审核"]

    S --> T["财务复核"]
    T --> U["锁定并过账"]
    U --> V["生成PDF及Excel请款单"]
    V --> W["登记发票"]
    W --> X["登记收款"]
    X --> Y["核销差异"]
```

六、可运行性

提供一条主要启动命令，例如：

```text
docker compose up --build
```

启动后必须可以：

1. 登录。
2. 建立项目。
3. 上传合同。
4. 建立合同版本。
5. 输入合同项目。
6. 批准合同。
7. 建立标准项目。
8. 审批映射。
9. 新建请款。
10. 输入本期数量。
11. 自动计算。
12. 审批并过账。
13. 生成PDF。
14. 登记发票。
15. 登记收款。
16. 查看文件。
17. 查看审计日志。

七、自动化测试

至少实现并实际执行：

1. 合同项目金额合计测试。
2. 合同版本不覆盖测试。
3. 数量超过合同上限测试。
4. 未批准变更不可请款测试。
5. 保留款计算测试。
6. 项目级保留款例外测试。
7. 保留款释放测试。
8. 税额及舍入测试。
9. 扣款税务处理测试。
10. 请款过账幂等测试。
11. 已过账请款不可编辑测试。
12. 发票与收款差异测试。
13. 文件路径穿越测试。
14. 文件哈希测试。
15. 项目权限隔离测试。
16. LLM关闭时核心流程测试。
17. LLM输出Schema验证测试。
18. 不同项目数据隔离测试。
19. PDF合计与数据库一致测试。
20. 备份一致性检查测试。

八、25-032验收场景

系统必须能够表达并验证：

1. 原始合同版本10,476,190。
2. 后续请款基准10,515,523作为不同版本或待确认调整。
3. 原合同版本仍可查看。
4. 两版本差额39,333被明确显示。
5. 第二期：

```text
施工金额 401,792
保留款 74,600
未税计价 327,192
税额 16,360
含税 343,552
```

6. 第三期：

```text
施工金额 0
保留款释放 980,496
税额 49,025
含税 1,029,521
```

7. 两笔扣款合计71,000。
8. 邮件建议开票金额1,900,024。
9. 系统显示邮件建议与第三期请款不一致，并要求人工说明。
10. 发票与实际收款差额90及30可以独立记录和核销。
11. 任何差异都不会自动修改合同金额。

九、24-023验收场景

系统必须能够：

1. 保存含税合同总价38,980,000。
2. 保存四个以上父级工程组。
3. 在父级下保存多个子项目。
4. 支持处、式、孔、m及m³等单位。
5. 支持多期累计数量。
6. 支持保留款。
7. 保证24-023的数据不会进入25-032。

十、文档生成验收

至少提供一份25-032示例请款单：

- A4可打印。
- 项目明细完整。
- 前期、本期、累计清楚。
- 保留款、税额及发票金额清楚。
- 数字与数据库一致。
- 不包含原合同印章或签名。
- 草稿和最终版可以区分。
- 生成文件进入文件存储，并可从网页预览和下载。

十一、完成报告

实施完成后输出：

1. 已完成模块。
2. 未完成模块及原因。
3. 实际运行命令。
4. 数据库迁移结果。
5. 测试结果。
6. 示例账号。
7. 示例项目。
8. 生成文件位置。
9. 安全及生产部署注意事项。
10. 下一阶段建议。

不要以“已经搭建基础框架”作为完成。只有核心业务闭环可运行并通过相应测试，才能标记完成。


REFERENCE

系统应遵循以下业务关系：

```text
项目
  └── 合同
       ├── 合同版本
       │    ├── 合同项目
       │    └── 付款及保留款规则
       ├── 变更
       ├── 请款
       │    ├── 请款明细
       │    ├── 保留款
       │    ├── 扣款
       │    ├── 审批
       │    └── 生成文件
       ├── 发票
       └── 收款
```

标准化关系：

```text
合同原始项目
  ├── 保留原始文字、单位、数量和单价
  ├── 规则及历史别名匹配
  ├── 可选语义检索及LLM候选
  ├── 人工转换审批
  └── 内部标准项目及成本版本
```

文件调用关系：

```text
数据库记录
  ├── storage_root_id
  ├── relative_path
  ├── original_name
  ├── sha256
  ├── document_type
  └── 业务关联

文件夹
  ├── 只读原件
  ├── 附件
  ├── OCR及抽取结果
  └── 系统生成的PDF及Excel版本
```

请优先保证：

1. 正确性。
2. 可追溯性。
3. 项目隔离。
4. 合同版本管理。
5. 财务计算可复算。
6. 人工审批边界。
7. 文件原件不可变。
8. 用户操作简单。
9. 可逐步扩展。
10. 系统在没有LLM时仍可完整运行。