'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge } from '@/components/ui/common';

interface AuditEntry { id: string; action: string; resource_type: string; resource_id: string; detail: string | null; created_at: string; }

export default function ProjectAuditPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [logs, setLogs] = useState<AuditEntry[]>([]);

  useEffect(() => {
    if (!user) return;
    api.get<AuditEntry[]>('/reports/audit-log').then(all => {
      // Filter to this project's resources (best-effort: filter by detail containing project_id)
      setLogs(all.filter(l => l.detail && l.detail.includes(projectId)).slice(0, 50));
    }).catch(() => setLogs([]));
  }, [user, projectId]);

  if (loading) return <div className="p-8">加载中...</div>;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader title="审计记录" subtitle="项目相关操作记录（最近50条）" />
      <Card>
        <CardHeader title={`操作记录 (${logs.length})`} />
        {logs.length === 0 ? <EmptyState message="暂无此项目的审计记录" /> : (
          <table className="data-table">
            <thead><tr><th>时间</th><th>操作</th><th>资源类型</th><th>详情</th></tr></thead>
            <tbody>
              {logs.map(l => (
                <tr key={l.id}>
                  <td className="font-mono text-xs text-slate-500">{l.created_at ? new Date(l.created_at).toLocaleString('zh-TW') : '—'}</td>
                  <td><StatusBadge status={l.action} /></td>
                  <td>{l.resource_type}</td>
                  <td className="text-xs text-slate-500 max-w-md truncate">{typeof l.detail === 'string' ? l.detail.substring(0, 80) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </main>
  );
}
