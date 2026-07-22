# Data Dictionary

Engineering Contract & Billing System — column-level reference for key tables.
Types shown as SQL/PostgreSQL equivalents. `NO` = NOT NULL. Mixin columns
(`created_at`, `updated_at`, `created_by`, `updated_by`, `organization_id`,
`deleted_at`) are included where present.

Legend:
- `PK` = primary key, `FK` = foreign key, `UK` = unique constraint
- Default `—` = none / application-supplied

---

## IDENTITY

### Table: organizations

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| code | VARCHAR(32) | NO | — | Unique tenant code (UK) |
| name | VARCHAR(256) | NO | — | Display name |
| default_currency | VARCHAR(8) | NO | 'TWD' | Default ISO currency |
| default_timezone | VARCHAR(64) | NO | 'Asia/Taipei' | Default IANA timezone |
| status | VARCHAR(16) | NO | 'ACTIVE' | Tenant status |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: users

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | FK → organizations.id |
| email | VARCHAR(256) | NO | — | Login email (UK with org) |
| display_name | VARCHAR(128) | NO | — | Full name |
| department | VARCHAR(128) | YES | — | Department |
| password_hash | VARCHAR(256) | YES | — | Hashed password (nullable for SSO) |
| external_id | VARCHAR(256) | YES | — | External identity provider id |
| status | VARCHAR(16) | NO | 'ACTIVE' | Account status |
| last_login_at | TIMESTAMPTZ | YES | — | Last successful login |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: roles

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| name | ENUM(UserRoleEnum) | NO | — | Role name (UK) |
| description | VARCHAR(512) | YES | — | Role description |

### Table: user_roles

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| user_id | UUID | NO | — | FK → users.id (cascade) |
| role_id | UUID | NO | — | FK → roles.id |
| organization_id | UUID | NO | — | FK → organizations.id |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

---

## PROJECT

### Table: companies

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| code | VARCHAR(32) | NO | — | Company code (UK with org) |
| name | VARCHAR(256) | NO | — | Company name |
| company_type | VARCHAR(32) | NO | — | OWNER, MAIN_CONTRACTOR, SUBCONTRACTOR, SUPPLIER, SELF |
| tax_id | VARCHAR(32) | YES | — | Tax identifier |
| address | TEXT | YES | — | Address |
| phone | VARCHAR(32) | YES | — | Phone |
| contact_person | VARCHAR(128) | YES | — | Contact person |
| status | VARCHAR(16) | NO | 'ACTIVE' | Status |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: projects

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| internal_project_code | VARCHAR(32) | NO | — | Internal code (UK with org) |
| project_name | VARCHAR(256) | NO | — | Project name |
| description | TEXT | YES | — | Description |
| project_manager_id | UUID | YES | — | FK → users.id |
| start_date | DATE | YES | — | Start date |
| planned_end_date | DATE | YES | — | Planned end |
| actual_end_date | DATE | YES | — | Actual end |
| status | VARCHAR(16) | NO | 'ACTIVE' | Status |
| currency | VARCHAR(8) | NO | 'TWD' | Project currency |
| default_tax_rate | NUMERIC(10,6) | NO | 0.05 | Default tax rate |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: project_members

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| project_id | UUID | NO | — | FK → projects.id (cascade) |
| user_id | UUID | NO | — | FK → users.id (cascade) |
| project_role | ENUM(ProjectMemberRoleEnum) | NO | — | PROJECT_MANAGER, COST_REVIEWER, PROJECT_USER, FINANCE_USER |
| status | VARCHAR(16) | NO | 'ACTIVE' | Membership status |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

---

## CONTRACT

### Table: contracts

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| project_id | UUID | NO | — | FK → projects.id (cascade) |
| external_contract_no | VARCHAR(64) | NO | — | External contract number |
| contract_name | VARCHAR(256) | NO | — | Contract name |
| customer_company_id | UUID | YES | — | FK → companies.id (customer) |
| contractor_company_id | UUID | YES | — | FK → companies.id (contractor) |
| signed_date | DATE | YES | — | Signed date |
| effective_date | DATE | YES | — | Effective date |
| currency | VARCHAR(8) | NO | 'TWD' | Contract currency |
| tax_mode | ENUM(TaxMode) | NO | EXCLUSIVE | EXCLUSIVE, INCLUSIVE, MIXED |
| tax_rate | NUMERIC(10,6) | NO | 0.05 | Tax rate |
| rounding_policy | ENUM(RoundingPolicy) | NO | ROUND_HALF_UP | Rounding policy |
| rounding_granularity | NUMERIC(18,2) | NO | 1 | Rounding step |
| original_amount_ex_tax | NUMERIC(18,2) | NO | 0 | Original ex-tax amount |
| original_tax_amount | NUMERIC(18,2) | NO | 0 | Original tax amount |
| original_amount_inc_tax | NUMERIC(18,2) | NO | 0 | Original incl-tax amount |
| status | VARCHAR(16) | NO | 'DRAFT' | Contract status |
| active_version_id | UUID | YES | — | FK → contract_versions.id (current approved) |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: contract_versions

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| contract_id | UUID | NO | — | FK → contracts.id (cascade) |
| version_no | INTEGER | NO | — | Version number (UK with contract) |
| version_type | ENUM(ContractVersionType) | NO | — | QUOTATION, SIGNED_CONTRACT, PROVISIONAL, INTERNAL_ADJUSTMENT, APPROVED_VARIATION |
| effective_date | DATE | YES | — | Effective date |
| amount_ex_tax | NUMERIC(18,2) | NO | 0 | Ex-tax amount |
| tax_amount | NUMERIC(18,2) | NO | 0 | Tax amount |
| amount_inc_tax | NUMERIC(18,2) | NO | 0 | Incl-tax amount |
| status | ENUM(ContractVersionStatus) | NO | DRAFT | DRAFT, UNDER_REVIEW, APPROVED, SUPERSEDED, REJECTED |
| change_reason | TEXT | YES | — | Reason for change |
| source_document_id | UUID | YES | — | Source document reference |
| approved_by | UUID | YES | — | Approver |
| approved_at | TIMESTAMPTZ | YES | — | Approval timestamp |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: contract_items

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| contract_version_id | UUID | NO | — | FK → contract_versions.id (cascade) |
| parent_item_id | UUID | YES | — | FK → contract_items.id (hierarchy) |
| line_no | VARCHAR(32) | NO | — | Line number |
| item_code | VARCHAR(64) | YES | — | Item code |
| source_description | TEXT | NO | — | Original description |
| normalized_description | TEXT | YES | — | Normalized description |
| unit | VARCHAR(32) | YES | — | Unit of measure |
| contract_quantity | NUMERIC(18,4) | NO | 0 | Contract quantity |
| unit_price | NUMERIC(18,2) | NO | 0 | Unit price |
| line_amount | NUMERIC(18,2) | NO | 0 | Line amount |
| calculation_method | ENUM(CalculationMethod) | NO | QUANTITY | QUANTITY, LUMP_SUM, PERCENTAGE, MILESTONE, ALLOWANCE, ADJUSTMENT, HEADING |
| tax_category | VARCHAR(32) | NO | 'STANDARD' | Tax category |
| retention_applicable | BOOLEAN | NO | true | Retention applies |
| retention_exempt_reason | TEXT | YES | — | Exemption reason |
| is_heading | BOOLEAN | NO | false | Heading row |
| is_billable | BOOLEAN | NO | true | Billable |
| sort_order | INTEGER | NO | 0 | Display order |
| source_page | INTEGER | YES | — | Source PDF page |
| source_bbox_json | JSONB | YES | — | Bounding box on source page |
| extraction_confidence | NUMERIC(5,2) | YES | — | Extraction confidence |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: payment_rules

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| contract_version_id | UUID | NO | — | FK → contract_versions.id (cascade) |
| contract_item_id | UUID | YES | — | FK → contract_items.id |
| rule_type | ENUM(PaymentRuleType) | NO | — | PROGRESS_PAYMENT, RETENTION_HOLD, RETENTION_RELEASE, MILESTONE_PAYMENT, ADVANCE_PAYMENT, DEDUCTION, TAX, ROUNDING, PENALTY |
| rule_name | VARCHAR(128) | NO | — | Rule name |
| rate | NUMERIC(10,6) | NO | 0 | Rule rate |
| condition_code | VARCHAR(64) | YES | — | Condition code |
| condition_description | TEXT | YES | — | Condition description |
| calculation_base | VARCHAR(32) | NO | 'CURRENT_PERIOD' | Calculation base |
| release_sequence | INTEGER | YES | — | Release sequence |
| effective_from | DATE | YES | — | Effective from |
| effective_to | DATE | YES | — | Effective to |
| is_active | BOOLEAN | NO | true | Active flag |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

---

## STANDARD

### Table: standard_items

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| code | VARCHAR(64) | NO | — | Standard item code (UK with org) |
| name | VARCHAR(256) | NO | — | Item name |
| category | VARCHAR(128) | YES | — | Category |
| unit | VARCHAR(32) | YES | — | Default unit |
| description | TEXT | YES | — | Description |
| is_active | BOOLEAN | NO | true | Active flag |
| sort_order | INTEGER | NO | 0 | Display order |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: standard_item_aliases

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| standard_item_id | UUID | NO | — | FK → standard_items.id (cascade) |
| alias_text | VARCHAR(256) | NO | — | Alias text (UK with item) |
| alias_source | VARCHAR(32) | NO | 'MANUAL' | MANUAL, EXTRACTED, LLM |
| is_approved | BOOLEAN | NO | false | Approved for matching |
| approved_by | UUID | YES | — | Approver |
| approved_at | DATE | YES | — | Approval date |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: standard_cost_versions

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| standard_item_id | UUID | NO | — | FK → standard_items.id (cascade) |
| version_no | INTEGER | NO | — | Version (UK with item) |
| effective_from | DATE | YES | — | Effective from |
| effective_to | DATE | YES | — | Effective to |
| unit_cost | NUMERIC(18,2) | NO | 0 | Unit cost |
| cost_basis | VARCHAR(32) | NO | 'STANDARD' | Cost basis |
| source | VARCHAR(32) | YES | — | Source |
| notes | TEXT | YES | — | Notes |
| status | VARCHAR(16) | NO | 'ACTIVE' | ACTIVE / SUPERSEDED |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

---

## BILLING

### Table: payment_applications

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| project_id | UUID | NO | — | FK → projects.id (cascade) |
| contract_id | UUID | NO | — | FK → contracts.id (cascade) |
| contract_version_id | UUID | NO | — | FK → contract_versions.id |
| application_no | VARCHAR(64) | NO | — | Application number (UK with contract+revision) |
| period_no | INTEGER | NO | — | Period number |
| period_start | DATE | NO | — | Period start |
| period_end | DATE | NO | — | Period end |
| application_date | DATE | NO | — | Application date |
| status | ENUM(ApplicationStatus) | NO | DRAFT | DRAFT…SUPERSEDED |
| currency | VARCHAR(8) | NO | 'TWD' | Application currency |
| gross_completed_amount | NUMERIC(18,2) | NO | 0 | Gross completed value |
| retention_held_amount | NUMERIC(18,2) | NO | 0 | Retention held |
| retention_released_amount | NUMERIC(18,2) | NO | 0 | Retention released |
| deduction_amount | NUMERIC(18,2) | NO | 0 | Deductions total |
| taxable_amount | NUMERIC(18,2) | NO | 0 | Taxable amount |
| tax_amount | NUMERIC(18,2) | NO | 0 | Tax amount |
| invoice_amount | NUMERIC(18,2) | NO | 0 | Net invoice amount |
| approved_amount | NUMERIC(18,2) | NO | 0 | Approved amount |
| revision_no | INTEGER | NO | 0 | Revision (0 = original) |
| supersedes_application_id | UUID | YES | — | FK → payment_applications.id |
| posted_at | TIMESTAMPTZ | YES | — | Posted timestamp |
| posted_action_id | VARCHAR(64) | YES | — | Idempotency key |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: payment_application_lines

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| payment_application_id | UUID | NO | — | FK → payment_applications.id (cascade) |
| contract_item_id | UUID | NO | — | FK → contract_items.id |
| contract_version_id | UUID | NO | — | FK → contract_versions.id |
| description_snapshot | TEXT | NO | — | Snapshot of item description |
| unit_snapshot | VARCHAR(32) | YES | — | Snapshot of unit |
| unit_price_snapshot | NUMERIC(18,2) | NO | — | Snapshot of unit price |
| previous_approved_quantity | NUMERIC(18,4) | NO | 0 | Prior cumulative qty |
| current_claimed_quantity | NUMERIC(18,4) | NO | 0 | Claimed this period |
| current_approved_quantity | NUMERIC(18,4) | NO | 0 | Approved this period |
| cumulative_approved_quantity | NUMERIC(18,4) | NO | 0 | Cumulative approved qty |
| current_completed_amount | NUMERIC(18,2) | NO | 0 | Completed amount this period |
| retention_rate | NUMERIC(10,6) | NO | 0 | Retention rate applied |
| retention_held | NUMERIC(18,2) | NO | 0 | Retention held this period |
| retention_released | NUMERIC(18,2) | NO | 0 | Retention released this period |
| deduction_amount | NUMERIC(18,2) | NO | 0 | Deduction this period |
| taxable_amount | NUMERIC(18,2) | NO | 0 | Taxable amount |
| tax_amount | NUMERIC(18,2) | NO | 0 | Tax amount |
| net_amount | NUMERIC(18,2) | NO | 0 | Net amount |
| calculation_method | VARCHAR(32) | NO | 'QUANTITY' | Calculation method |
| user_explanation | TEXT | YES | — | User explanation |
| validation_status | VARCHAR(16) | NO | 'PENDING' | PENDING, OK, ERROR |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: retention_entries

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| project_id | UUID | NO | — | FK → projects.id (cascade) |
| contract_id | UUID | NO | — | FK → contracts.id (cascade) |
| payment_application_id | UUID | YES | — | FK → payment_applications.id |
| contract_item_id | UUID | YES | — | FK → contract_items.id |
| entry_type | ENUM(RetentionEntryType) | NO | — | HOLD, RELEASE, ADJUSTMENT, REVERSAL |
| amount | NUMERIC(18,2) | NO | — | Amount |
| description | TEXT | YES | — | Description |
| reversal_of_id | UUID | YES | — | FK → retention_entries.id (reversal link) |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: variations

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| project_id | UUID | NO | — | FK → projects.id (cascade) |
| contract_id | UUID | NO | — | FK → contracts.id (cascade) |
| contract_item_id | UUID | YES | — | FK → contract_items.id |
| variation_no | VARCHAR(64) | NO | — | Variation number (UK with contract) |
| variation_type | ENUM(VariationType) | NO | — | PRICE_ADJUSTMENT, QUANTITY_ADJUSTMENT, SCOPE_CHANGE, LUMP_SUM_ADJUSTMENT |
| description | TEXT | YES | — | Description |
| reason | TEXT | YES | — | Reason |
| amount_ex_tax | NUMERIC(18,2) | NO | 0 | Ex-tax amount |
| tax_amount | NUMERIC(18,2) | NO | 0 | Tax amount |
| amount_inc_tax | NUMERIC(18,2) | NO | 0 | Incl-tax amount |
| quantity_delta | NUMERIC(18,4) | NO | 0 | Quantity delta |
| effective_date | DATE | YES | — | Effective date |
| status | ENUM(VariationStatus) | NO | DRAFT | DRAFT, UNDER_REVIEW, APPROVED, REJECTED, SUPERSEDED |
| approved_by | UUID | YES | — | Approver |
| approved_at | DATE | YES | — | Approval date |
| source_document_id | UUID | YES | — | Source document reference |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

---

## FINANCE

### Table: deductions

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| project_id | UUID | NO | — | FK → projects.id (cascade) |
| contract_id | UUID | NO | — | FK → contracts.id (cascade) |
| payment_application_id | UUID | YES | — | FK → payment_applications.id |
| deduction_no | VARCHAR(64) | NO | — | Deduction number (UK with contract) |
| deduction_type | ENUM(DeductionType) | NO | — | ADVANCE_OFFSET, MATERIAL_DEDUCTION, EQUIPMENT_DEDUCTION, QUALITY_PENALTY, OTHER |
| description | TEXT | YES | — | Description |
| reason | TEXT | YES | — | Reason |
| amount | NUMERIC(18,2) | NO | — | Deduction amount |
| tax_treatment | ENUM(TaxTreatment) | NO | TAXABLE | TAXABLE, NON_TAXABLE, TAX_ADJUSTMENT |
| tax_amount | NUMERIC(18,2) | NO | 0 | Tax amount |
| effective_date | DATE | YES | — | Effective date |
| status | ENUM(DeductionStatus) | NO | DRAFT | DRAFT, APPROVED, REJECTED |
| approved_by | UUID | YES | — | Approver |
| approved_at | DATE | YES | — | Approval date |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: invoices

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| project_id | UUID | NO | — | FK → projects.id (cascade) |
| contract_id | UUID | NO | — | FK → contracts.id (cascade) |
| invoice_no | VARCHAR(64) | NO | — | Invoice number (UK with contract) |
| invoice_type | ENUM(InvoiceType) | NO | STANDARD | STANDARD, DEBIT_NOTE, CREDIT_NOTE |
| issue_date | DATE | YES | — | Issue date |
| due_date | DATE | YES | — | Due date |
| amount_ex_tax | NUMERIC(18,2) | NO | 0 | Ex-tax amount |
| tax_amount | NUMERIC(18,2) | NO | 0 | Tax amount |
| amount_inc_tax | NUMERIC(18,2) | NO | 0 | Incl-tax amount |
| tax_rate | NUMERIC(10,6) | NO | 0.05 | Tax rate applied |
| status | ENUM(InvoiceStatus) | NO | DRAFT | DRAFT, ISSUED, PARTIALLY_PAID, PAID, VOID |
| source | VARCHAR(32) | NO | 'MANUAL' | MANUAL, GENERATED |
| notes | TEXT | YES | — | Notes |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: collections

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| project_id | UUID | NO | — | FK → projects.id (cascade) |
| contract_id | UUID | NO | — | FK → contracts.id (cascade) |
| receipt_no | VARCHAR(64) | NO | — | Receipt number (UK with contract) |
| receipt_date | DATE | YES | — | Receipt date |
| amount_received | NUMERIC(18,2) | NO | — | Amount received |
| payment_method | VARCHAR(32) | NO | 'BANK_TRANSFER' | Payment method |
| bank_reference | VARCHAR(128) | YES | — | Bank reference |
| notes | TEXT | YES | — | Notes |
| status | ENUM(CollectionStatus) | NO | CONFIRMED | PENDING, CONFIRMED, REVERSED |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: item_mappings

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| project_id | UUID | NO | — | FK → projects.id (cascade) |
| contract_item_id | UUID | NO | — | FK → contract_items.id |
| standard_item_id | UUID | NO | — | FK → standard_items.id |
| mapping_type | ENUM(MappingType) | NO | ONE_TO_ONE | ONE_TO_ONE, ONE_TO_MANY, MANY_TO_ONE |
| match_method | ENUM(MatchMethod) | NO | MANUAL | MANUAL, EXACT_ALIAS, RULE, FULLTEXT, VECTOR, LLM |
| unit_compatibility | ENUM(UnitCompatibility) | NO | SAME | SAME, CONVERTIBLE, INCOMPATIBLE, UNKNOWN |
| conversion_factor | NUMERIC(18,6) | NO | 1 | Unit conversion factor |
| confidence | NUMERIC(5,2) | YES | — | Match confidence (0-100) |
| status | ENUM(MappingStatus) | NO | SUGGESTED | SUGGESTED, PENDING_REVIEW, APPROVED, REJECTED, NEEDS_CLARIFICATION |
| approved_by | UUID | YES | — | Approver |
| approved_at | UUID | YES | — | Approval timestamp |
| llm_reasoning | TEXT | YES | — | LLM reasoning text |
| llm_output | JSONB | YES | — | Raw LLM output |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

---

## FILES

### Table: documents

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| project_id | UUID | YES | — | FK → projects.id |
| storage_root_id | UUID | NO | — | FK → storage_roots.id |
| original_name | VARCHAR(512) | NO | — | Original filename |
| stored_name | VARCHAR(512) | NO | — | Stored filename |
| relative_path | VARCHAR(1024) | NO | — | Path relative to storage root |
| document_type | VARCHAR(32) | NO | — | CONTRACT, APPLICATION, INVOICE, etc. |
| mime_type | VARCHAR(128) | NO | — | MIME type |
| file_extension | VARCHAR(16) | NO | — | File extension |
| size_bytes | INTEGER | NO | — | File size in bytes |
| sha256 | VARCHAR(64) | NO | — | Content hash |
| version_no | INTEGER | NO | 1 | Document version |
| is_original | BOOLEAN | NO | true | Is original upload |
| is_generated | BOOLEAN | NO | false | Is generated document |
| is_immutable | BOOLEAN | NO | false | Immutable flag |
| uploaded_at | TIMESTAMPTZ | NO | now() | Upload timestamp |
| ocr_status | VARCHAR(16) | NO | 'NOT_REQUIRED' | OCR status |
| extraction_status | VARCHAR(16) | NO | 'NOT_REQUIRED' | Extraction status |
| retention_status | VARCHAR(16) | NO | 'ACTIVE' | Retention status |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: document_templates (migration 016)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| project_id | UUID | YES | — | FK → projects.id (project-scoped, else org-wide) |
| name | VARCHAR(256) | NO | — | Template name |
| template_type | VARCHAR(32) | NO | — | BILLING, INVOICE, etc. |
| file_path | VARCHAR(512) | NO | — | Template file path |
| effective_from | DATE | YES | — | Effective from |
| effective_to | DATE | YES | — | Effective to |
| is_active | BOOLEAN | NO | true | Active flag |
| deleted_at | TIMESTAMPTZ | YES | — | Soft-delete marker |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: generated_documents (migration 016)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| payment_application_id | UUID | YES | — | FK → payment_applications.id |
| document_template_id | UUID | YES | — | FK → document_templates.id |
| doc_type | VARCHAR(16) | NO | — | PDF, EXCEL |
| file_path | VARCHAR(512) | NO | — | Output file path |
| is_final | BOOLEAN | NO | false | Final version flag |
| version_no | INTEGER | NO | 1 | Generated version number |
| generated_by | UUID | YES | — | Generating user id |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

---

## AUDIT

### Table: approval_workflows

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| name | VARCHAR(128) | NO | — | Workflow name |
| resource_type | VARCHAR(32) | NO | — | CONTRACT_VERSION, ITEM_MAPPING, APPLICATION, etc. |
| condition_config | JSONB | YES | — | Activation conditions |
| is_active | BOOLEAN | NO | true | Active flag |
| created_by | UUID | YES | — | Audit — creator |
| updated_by | UUID | YES | — | Audit — updater |
| created_at | TIMESTAMPTZ | NO | now() | Row created |
| updated_at | TIMESTAMPTZ | NO | now() | Row updated |

### Table: audit_logs

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| id | UUID | NO | gen_random_uuid() | PK |
| organization_id | UUID | NO | — | Tenant isolation |
| user_id | UUID | YES | — | Acting user (FK, logical) |
| action | VARCHAR(64) | NO | — | Action verb (CREATE, UPDATE, DELETE, APPROVE…) |
| resource_type | VARCHAR(32) | NO | — | Affected resource type |
| resource_id | VARCHAR(64) | YES | — | Affected resource id (string) |
| detail | JSONB | YES | — | Change detail / diff |
| ip_address | VARCHAR(45) | YES | — | Source IP |
| created_at | TIMESTAMPTZ | NO | now() | Event timestamp |

---

## Enum Reference

| Enum | Values |
|---|---|
| TaxMode | EXCLUSIVE, INCLUSIVE, MIXED |
| RoundingPolicy | ROUND_HALF_UP, ROUND_DOWN, BANKERS |
| ContractVersionType | QUOTATION, SIGNED_CONTRACT, PROVISIONAL, INTERNAL_ADJUSTMENT, APPROVED_VARIATION |
| ContractVersionStatus | DRAFT, UNDER_REVIEW, APPROVED, SUPERSEDED, REJECTED |
| CalculationMethod | QUANTITY, LUMP_SUM, PERCENTAGE, MILESTONE, ALLOWANCE, ADJUSTMENT, HEADING |
| PaymentRuleType | PROGRESS_PAYMENT, RETENTION_HOLD, RETENTION_RELEASE, MILESTONE_PAYMENT, ADVANCE_PAYMENT, DEDUCTION, TAX, ROUNDING, PENALTY |
| ApplicationStatus | DRAFT, VALIDATING, NEEDS_CHANGES, SUBMITTED, PROJECT_APPROVED, FINANCE_APPROVED, POSTED, GENERATED, SENT, REJECTED, CANCELLED, SUPERSEDED |
| RetentionEntryType | HOLD, RELEASE, ADJUSTMENT, REVERSAL |
| VariationType | PRICE_ADJUSTMENT, QUANTITY_ADJUSTMENT, SCOPE_CHANGE, LUMP_SUM_ADJUSTMENT |
| VariationStatus | DRAFT, UNDER_REVIEW, APPROVED, REJECTED, SUPERSEDED |
| DeductionType | ADVANCE_OFFSET, MATERIAL_DEDUCTION, EQUIPMENT_DEDUCTION, QUALITY_PENALTY, OTHER |
| TaxTreatment | TAXABLE, NON_TAXABLE, TAX_ADJUSTMENT |
| DeductionStatus | DRAFT, APPROVED, REJECTED |
| InvoiceType | STANDARD, DEBIT_NOTE, CREDIT_NOTE |
| InvoiceStatus | DRAFT, ISSUED, PARTIALLY_PAID, PAID, VOID |
| CollectionStatus | PENDING, CONFIRMED, REVERSED |
| MappingType | ONE_TO_ONE, ONE_TO_MANY, MANY_TO_ONE |
| MatchMethod | MANUAL, EXACT_ALIAS, RULE, FULLTEXT, VECTOR, LLM |
| UnitCompatibility | SAME, CONVERTIBLE, INCOMPATIBLE, UNKNOWN |
| MappingStatus | SUGGESTED, PENDING_REVIEW, APPROVED, REJECTED, NEEDS_CLARIFICATION |
| UserRoleEnum | SYSTEM_ADMIN, CONTRACT_ADMIN, PROJECT_USER, PROJECT_MANAGER, COST_REVIEWER, FINANCE_REVIEWER, FINANCE_USER, AUDITOR, VIEWER |
| ProjectMemberRoleEnum | PROJECT_MANAGER, COST_REVIEWER, PROJECT_USER, FINANCE_USER |
