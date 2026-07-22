'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge, formatMoney } from '@/components/ui/common';

type ReportKey = 'project-summary' | 'retention-balances' | 'uninvoiced' | 'invoice-outstanding' | 'collection-variances' | 'cost-margin' | 'pending-exceptions';

const reports: { key: ReportKey; label: string; icon: string }[] = [
  { key: 'project-summary', label: '项目商业汇总', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { key: 'retention-balances', label: '保留款余额', icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z' },
  { key: 'uninvoiced', label: '未开票已批准金额', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { key: 'invoice-outstanding', label: '发票未清金额', icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1' },
  { key: 'collection-variances', label: '收款差异', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
  { key: 'cost-margin', label: '成本毛利分析', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { key: 'pending-exceptions', label: '待处理异常', icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' },
];

export default function ReportsPage() {
  const { user, loading } = useAuth();
  const [activeReport, setActiveReport] = useState<ReportKey>('project-summary');
  const [data, setData] = useState<Record<string, any>[]>([]);
  const [loadingReport, setLoadingReport] = useState(false);

  useEffect(() => {
    if (!user) return;
    setLoadingReport(true);
    api.get<Record<string, any>[]>(`/reports/${activeReport}`)
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoadingReport(false));
  }, [user, activeReport]);

  if (loading) return null;

  const columns = data.length > 0 ? Object.keys(data[0]) : [];

  return (
    <>
      <PageHeader title="报表中心" subtitle="8 种 DB 视图报表 + 审计日志" />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader title="报表列表" />
            <div className="p-2 space-y-1">
              {reports.map((r) => (
                <button
                  key={r.key}
                  onClick={() => setActiveReport(r.key)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-md transition-colors duration-200 cursor-pointer ${
                    activeReport === r.key
                      ? 'bg-orange-50 text-orange-700'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={r.icon} />
                  </svg>
                  <span>{r.label}</span>
                </button>
              ))}
            </div>
          </Card>
        </div>

        <div className="lg:col-span-3">
          <Card>
            <CardHeader
              title={reports.find(r => r.key === activeReport)?.label || ''}
              actions={<span className="text-xs text-slate-400">{data.length} 条记录</span>}
            />
            <div className="overflow-x-auto scrollbar-thin">
              {loadingReport ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-orange-500"></div>
                </div>
              ) : data.length === 0 ? (
                <EmptyState message="暂无数据" />
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      {columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((row, i) => (
                      <tr key={i}>
                        {columns.map((col) => {
                          const val = row[col];
                          const isMoney = ['amount', 'balance', 'total_held', 'total_released', 'total_adjustment', 'contract_value', 'invoiced_to_date', 'gross_completed', 'retention_held', 'expected', 'received', 'variance', 'outstanding_amount', 'uninvoiced_amount', 'linked_amount', 'standard_cost', 'margin', 'allocated_amount'].includes(col);
                          const isStatus = col === 'status';
                          return (
                        <td key={col} className={isMoney ? 'num' : ''}>
                          {isStatus ? (
                            <StatusBadge status={String(val)} />
                          ) : isMoney ? (
                            formatMoney(val)
                          ) : typeof val === 'string' && val.length > 50 ? (
                            val.substring(0, 50) + '...'
                          ) : (
                            String(val || '—')
                          )}
                        </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
