'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge } from '@/components/ui/common';

interface AuditLogEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  detail: string | null;
  created_at: string;
}

export default function AuditLogPage() {
  const { user, loading } = useAuth();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);

  useEffect(() => {
    if (!user) return;
    api.get<AuditLogEntry[]>('/reports/audit-log').then(setLogs).catch(() => setLogs([]));
  }, [user]);

  if (loading) return null;

  return (
    <>
      <PageHeader title="审计日志" subtitle="追加只读 · 不可编辑 · 最近 100 条" />
      <Card>
        <CardHeader title="操作记录" actions={<span className="text-xs text-slate-400">{logs.length} 条记录</span>} />
        <div className="overflow-x-auto scrollbar-thin">
          {logs.length === 0 ? (
            <EmptyState message="暂无审计日志记录" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>操作</th>
                  <th>资源类型</th>
                  <th>资源 ID</th>
                  <th>详情</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td className="font-mono text-xs text-slate-500">{log.created_at ? new Date(log.created_at).toLocaleString('zh-TW') : '—'}</td>
                    <td><StatusBadge status={log.action} /></td>
                    <td>{log.resource_type || '—'}</td>
                    <td className="font-mono text-xs">{log.resource_id ? log.resource_id.substring(0, 8) + '...' : '—'}</td>
                    <td className="text-xs text-slate-500 max-w-xs truncate">{log.detail || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </>
  );
}
