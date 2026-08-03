'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge } from '@/components/ui/common';
import { FilterBar } from '@/components/ui/FilterBar';

interface AuditLogEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  detail: string | null;
  created_at: string;
}

function exportCSV(filename: string, rows: Record<string, any>[]) {
  if (rows.length === 0) return;
  const cols = Object.keys(rows[0]);
  const header = cols.join(',');
  const body = rows.map(row =>
    cols.map(col => {
      const v = row[col];
      if (v === null || v === undefined) return '';
      const s = typeof v === 'object' ? JSON.stringify(v) : String(v).replace(/"/g, '""');
      return /[",\n]/.test(s) ? `"${s}"` : s;
    }).join(',')
  ).join('\n');
  const csv = '\uFEFF' + header + '\n' + body;
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AuditLogPage() {
  const { user, loading } = useAuth();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [filterAction, setFilterAction] = useState('');
  const [filterResource, setFilterResource] = useState('');
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  useEffect(() => {
    if (!user) return;
    api.get<AuditLogEntry[]>('/reports/audit-log').then(setLogs).catch(() => setLogs([]));
  }, [user]);

  const actionOptions = useMemo(() => {
    const set = new Set(logs.map(l => l.action));
    return Array.from(set).sort();
  }, [logs]);

  const resourceOptions = useMemo(() => {
    const set = new Set(logs.map(l => l.resource_type).filter(Boolean));
    return Array.from(set).sort();
  }, [logs]);

  const filtered = useMemo(() => {
    return logs.filter(l => {
      if (filterAction && l.action !== filterAction) return false;
      if (filterResource && l.resource_type !== filterResource) return false;
      if (search) {
        const s = search.toLowerCase();
        if (!l.action.toLowerCase().includes(s) &&
            !l.resource_type.toLowerCase().includes(s) &&
            !(l.detail || '').toLowerCase().includes(s)) return false;
      }
      if (dateFrom && l.created_at && l.created_at.substring(0, 10) < dateFrom) return false;
      if (dateTo && l.created_at && l.created_at.substring(0, 10) > dateTo) return false;
      return true;
    });
  }, [logs, filterAction, filterResource, search, dateFrom, dateTo]);

  if (loading) return null;

  return (
    <>
      <PageHeader title="审计日志" subtitle="追加只读 · 不可编辑 · 最近 100 条" />
      <FilterBar
        filters={[
          { label: '操作', value: filterAction, options: actionOptions.map(a => ({ label: a, value: a })), onChange: setFilterAction },
          { label: '资源类型', value: filterResource, options: resourceOptions.map(r => ({ label: r, value: r })), onChange: setFilterResource },
        ]}
        searchValue={search}
        onSearchChange={setSearch}
      />
      <div className="flex items-center gap-3 mb-4">
        <label className="text-xs text-slate-500">起</label>
        <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="input-field text-sm py-1.5" />
        <label className="text-xs text-slate-500">止</label>
        <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="input-field text-sm py-1.5" />
        <button onClick={() => { setFilterAction(''); setFilterResource(''); setSearch(''); setDateFrom(''); setDateTo(''); }} className="btn-secondary text-sm px-3 py-1.5">清除</button>
        <button onClick={() => exportCSV('audit-log.csv', filtered)} disabled={filtered.length === 0} className="btn-primary text-sm px-3 py-1.5 ml-auto disabled:opacity-50">导出 Excel</button>
      </div>
      <Card>
        <CardHeader title="操作记录" actions={<span className="text-xs text-slate-400">{filtered.length} / {logs.length} 条</span>} />
        <div className="overflow-x-auto scrollbar-thin">
          {filtered.length === 0 ? (
            <EmptyState message="暂无匹配的审计日志记录" />
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
                {filtered.map((log) => (
                  <tr key={log.id}>
                    <td className="font-mono text-xs text-slate-500">{log.created_at ? new Date(log.created_at).toLocaleString('zh-TW') : '—'}</td>
                    <td><StatusBadge status={log.action} /></td>
                    <td>{log.resource_type || '—'}</td>
                    <td className="font-mono text-xs">{log.resource_id ? log.resource_id.substring(0, 8) + '...' : '—'}</td>
                    <td className="text-xs text-slate-500 max-w-xs truncate">{log.detail ? (typeof log.detail === 'string' ? log.detail : JSON.stringify(log.detail)) : '—'}</td>
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
