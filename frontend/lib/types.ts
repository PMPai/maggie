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
}

export interface Application {
  id: string;
  project_id: string;
  contract_id: string;
  application_no: string;
  period_no: number;
  status: string;
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
