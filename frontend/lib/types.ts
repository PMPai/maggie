export interface User {
  id: string;
  email: string;
  display_name: string;
  organization_id: string;
  roles: string[];
}

export interface Project {
  id: string;
  internal_project_code: string;
  project_name: string;
  description: string | null;
  status: string;
  currency: string;
  default_tax_rate: string;
  special_fund_description?: string | null;
}

export interface Contract {
  id: string;
  project_id: string;
  external_contract_no: string;
  contract_name: string;
  currency: string;
  tax_mode: string;
  tax_rate: string;
  original_amount_ex_tax: string;
  original_tax_amount: string;
  original_amount_inc_tax: string;
  status: string;
  active_version_id: string | null;
}

export interface ContractVersion {
  id: string;
  contract_id: string;
  version_no: number;
  version_type: string;
  amount_ex_tax: string;
  tax_amount: string;
  amount_inc_tax: string;
  status: string;
  change_reason: string | null;
  source_document_id: string | null;
}

export interface ContractItem {
  id: string;
  contract_version_id: string;
  parent_item_id: string | null;
  line_no: string;
  item_code: string | null;
  source_description: string;
  unit: string | null;
  contract_quantity: string;
  unit_price: string;
  line_amount: string;
  calculation_method: string;
  is_heading: boolean;
  is_billable: boolean;
  retention_applicable: boolean;
  sort_order: number;
  expected_payment_date?: string | null;
  actual_payment_date?: string | null;
}

export interface Application {
  id: string;
  project_id: string;
  contract_id: string;
  application_no: string;
  period_no: number;
  status: string;
  created_by?: string | null;
  gross_completed_amount: string;
  retention_held_amount: string;
  retention_released_amount: string;
  deduction_amount: string;
  taxable_amount: string;
  tax_amount: string;
  invoice_amount: string;
}

export interface ApplicationLine {
  id: string;
  contract_item_id: string;
  description_snapshot: string;
  unit_snapshot: string | null;
  unit_price_snapshot: string;
  previous_approved_quantity: string;
  current_claimed_quantity: string;
  current_approved_quantity: string;
  cumulative_approved_quantity: string;
  current_completed_amount: string;
  retention_held: string;
  taxable_amount: string;
  tax_amount: string;
  net_amount: string;
  validation_status: string;
}

export interface Variation {
  id: string;
  variation_no: string;
  variation_type: string;
  description: string;
  amount_ex_tax: number;
  tax_amount: number;
  amount_inc_tax: number;
  quantity_delta: number;
  status: string;
  effective_date: string;
}

export interface VariationLine {
  id: string;
  contract_item_id: string;
  quantity_delta: number;
  amount_delta: number;
  description: string;
}

export interface Deduction {
  id: string;
  deduction_no: string;
  deduction_type: string;
  description: string;
  amount: number;
  tax_treatment: string;
  tax_amount: number;
  status: string;
  effective_date: string;
}

export interface RetentionEntry {
  id: string;
  entry_type: string;
  amount: number;
  description: string;
  created_at: string;
}

export interface Invoice {
  id: string;
  invoice_no: string;
  invoice_type: string;
  issue_date: string;
  amount_ex_tax: number;
  tax_amount: number;
  amount_inc_tax: number;
  status: string;
  source: string;
}

export interface Collection {
  id: string;
  receipt_no: string;
  receipt_date: string;
  amount_received: number;
  status: string;
  payment_method: string;
}

export interface CollectionAllocation {
  id: string;
  invoice_id: string;
  allocated_amount: number;
}

export interface FinancialAdjustment {
  id: string;
  adjustment_no: string;
  adjustment_type: string;
  amount: number;
  description: string;
  status: string;
}

export interface StandardItem {
  id: string;
  code: string;
  name: string;
  category: string;
  unit: string;
  description: string;
  is_active: boolean;
  latest_unit_cost?: string | number | null;
}

export interface ItemMapping {
  id: string;
  contract_item_id: string;
  standard_item_id: string;
  mapping_type: string;
  match_method: string;
  status: string;
  confidence: number;
}

export interface MatchingReview {
  id: string;
  contract_item_id: string;
  review_type: string;
  status: string;
  decision: string;
}

export interface ApplicationTotals {
  gross_completed_amount: number;
  retention_held_amount: number;
  retention_released_amount: number;
  deduction_amount: number;
  taxable_amount: number;
  tax_amount: number;
  invoice_amount: number;
}

export interface DashboardSummary {
  total_contract_amount: string;
  gross_completed_total: string;
  approved_total: string;
  invoiced_total: string;
  collected_total: string;
  retention_held_total: string;
  invoice_outstanding_total: string;
  pending_variations: number;
  pending_applications: number;
  pending_mappings: number;
  overclaim_exceptions: number;
  contract_version_diffs: number;
  per_project: {
    project_id: string;
    code: string;
    name: string;
    contract_amount: string;
    approved_total: string;
    retention_held: string;
  }[];
  recent_audit: { id: string; action: string; created_at: string | null }[];
}

export interface PendingApproval {
  resource_type: string;
  resource_id: string;
  description: string;
  project_id: string | null;
  project_code: string | null;
  amount: string | null;
  waiting_for_role: string;
  created_at: string | null;
  approve_url: string | null;
  reject_url: string | null;
  detail_url: string | null;
}

export interface MasterBudgetRow {
  contract_item_id: string;
  parent_item_id: string | null;
  line_no: string;
  description: string;
  unit: string | null;
  contract_quantity: string;
  unit_price: string;
  approved_quantity: string;
  approved_unit_price: string;
  variation_delta: string;
  previous_cumulative_quantity: string;
  current_period_quantity: string;
  cumulative_approved_quantity: string;
  remaining_quantity: string;
  completed_amount: string;
  claimed_amount: string;
  retention_balance: string;
  invoiced_amount: string;
  collected_amount: string;
  standard_cost_per_unit: string | null;
  standard_cost_total: string | null;
  expected_margin: string | null;
  margin_pct: string | null;
  price_variance: string | null;
  expected_payment_date: string | null;
  actual_payment_date: string | null;
  exception_status: 'none' | 'overclaim' | 'unmapped';
}

export interface MasterBudgetResponse {
  contract_id: string;
  contract_version_id: string;
  rows: MasterBudgetRow[];
}

export interface FileInboxItem {
  id: string;
  original_name: string;
  document_type: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  version_no: number;
  is_original: boolean;
  is_immutable: boolean;
  ocr_status: string;
  ocr_text: string | null;
  project_id: string | null;
  uploaded_at: string | null;
}
