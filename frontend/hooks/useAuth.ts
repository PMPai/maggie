'use client';
import type { User } from '@/lib/types';

const LOCAL_USER: User = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'local@maggie',
  display_name: 'Local User',
  roles: ['SYSTEM_ADMIN', 'CONTRACT_ADMIN', 'FINANCE_REVIEWER', 'FINANCE_USER', 'COST_REVIEWER', 'PROJECT_MANAGER', 'PROJECT_USER', 'AUDITOR', 'VIEWER'],
};

export function useAuth() {
  const user: User | null = LOCAL_USER;
  const loading = false;

  const login = async (_email: string, _password: string) => LOCAL_USER;
  const logout = async () => {};

  return { user, loading, login, logout };
}