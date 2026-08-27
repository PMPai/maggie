export const ROLE_LABELS: Record<string, string> = {
  SYSTEM_ADMIN: '系统管理员',
  CONTRACT_ADMIN: '合同管理员',
  PROJECT_MANAGER: '项目负责人',
  PROJECT_USER: '项目人员',
  COST_REVIEWER: '造价复核',
  FINANCE_REVIEWER: '财务复核',
  FINANCE_USER: '财务人员',
  AUDITOR: '审计员',
  VIEWER: '只读用户',
};

export const CATEGORY_LABELS: Record<string, string> = {
  ADMIN: '管理员',
  FINANCE: '财务',
  LEADER: '项目',
  AUDITOR: '审计',
  VIEWER: '只读',
};

export const CATEGORY_COLORS: Record<string, string> = {
  ADMIN: 'bg-red-100 text-red-700',
  FINANCE: 'bg-blue-100 text-blue-700',
  LEADER: 'bg-green-100 text-green-700',
  AUDITOR: 'bg-purple-100 text-purple-700',
  VIEWER: 'bg-slate-100 text-slate-600',
};

export const ROLE_TO_CATEGORY: Record<string, string> = {
  SYSTEM_ADMIN: 'ADMIN',
  CONTRACT_ADMIN: 'ADMIN',
  FINANCE_REVIEWER: 'FINANCE',
  FINANCE_USER: 'FINANCE',
  COST_REVIEWER: 'FINANCE',
  PROJECT_MANAGER: 'LEADER',
  PROJECT_USER: 'LEADER',
  AUDITOR: 'AUDITOR',
  VIEWER: 'VIEWER',
};

export function getUserCategory(roles: string[]): string {
  const categories = new Set<string>();
  for (const r of roles) {
    const cat = ROLE_TO_CATEGORY[r];
    if (cat) categories.add(cat);
  }
  if (categories.has('ADMIN')) return 'ADMIN';
  if (categories.has('FINANCE')) return 'FINANCE';
  if (categories.has('LEADER')) return 'LEADER';
  if (categories.has('AUDITOR')) return 'AUDITOR';
  return 'VIEWER';
}

export function hasCategory(roles: string[], category: string): boolean {
  return roles.some(r => ROLE_TO_CATEGORY[r] === category);
}

export function canAccess(roles: string[], requiredCategories: string[]): boolean {
  if (requiredCategories.length === 0) return true;
  return requiredCategories.some(cat => hasCategory(roles, cat));
}

export function roleLabel(role: string): string {
  return ROLE_LABELS[role] || role;
}

export function categoryLabel(cat: string): string {
  return CATEGORY_LABELS[cat] || cat;
}

export function categoryColor(cat: string): string {
  return CATEGORY_COLORS[cat] || 'bg-slate-100 text-slate-600';
}

export interface GroupInfo {
  id: string;
  name: string;
  category: string;
  description?: string;
  status: string;
  is_default: boolean;
  roles: { id: string; name: string }[];
  member_count: number;
  created_at?: string;
}

export interface GroupDetail extends GroupInfo {
  members: { id: string; display_name: string; email: string; department?: string; joined_at?: string }[];
}

export interface UserWithGroups {
  id: string;
  email: string;
  display_name: string;
  department?: string;
  status: string;
  roles: string[];
  groups: { id: string; name: string; category: string }[];
  last_login_at?: string;
  created_at?: string;
}