'use client';
import { useAuth } from '@/hooks/useAuth';
import { Suspense, useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { api } from '@/lib/api';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge, formatMoney } from '@/components/ui/common';

type ReportKey =
  | 'project-summary'
  | 'retention-balances'
  | 'uninvoiced'
  | 'invoice-outstanding'
  | 'collection-variances'
  | 'cost-margin'
  | 'pending-exceptions'
  | 'contract-item-balances'
  | 'project-overview'
  | 'application-history'
  | 'receivables-aging';

type ReportEntry = { key: ReportKey; label: string; icon: string; comingSoon?: boolean };

const reports: ReportEntry[] = [
  { key: 'contract-item-balances', label: '合同项目余额', icon: 'M4 6h16M4 12h16M4 18h7' },
  { key: 'project-summary', label: '项目商业汇总', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { key: 'retention-balances', label: '保留款余额', icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z' },
  { key: 'uninvoiced', label: '未开票已批准金额', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { key: 'invoice-outstanding', label: '发票未清金额', icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1' },
  { key: 'collection-variances', label: '收款差异', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
  { key: 'cost-margin', label: '成本毛利分析', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { key: 'pending-exceptions', label: '待处理异常', icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' },
  { key: 'project-overview', label: '项目合同总览', icon: 'M4 6h16M4 12h16M4 18h7', comingSoon: true },
  { key: 'application-history', label: '请款历史', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z', comingSoon: true },
  { key: 'receivables-aging', label: '应收账龄', icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z', comingSoon: true },
];

const MONEY_HINTS = [
  'amount', 'balance', 'total_held', 'total_released', 'total_adjustment',
  'contract_value', 'invoiced_to_date', 'gross_completed', 'retention_held', 'expected',
  'received', 'variance', 'outstanding_amount', 'uninvoiced_amount', 'linked_amount',
  'standard_cost', 'margin', 'allocated_amount', 'amount_inc_tax', 'amount_ex_tax',
  'tax_amount', 'unit_price', 'line_amount', 'completed_amount', 'claimed_amount',
  'retention_balance', 'collected_amount', 'expected_margin',
];

const COLUMN_LABELS: Record<string, string> = {
  project_id: '项目ID', project_code: '项目编号', project_name: '项目名称',
  contract_id: '合同ID', contract_no: '合同编号', contract_name: '合同名称',
  contract_value: '合同金额', contract_amount: '合同金额',
  org_id: '组织ID', organization_id: '组织ID',
  gross_completed: '累计完成金额', gross_completed_amount: '累计完成金额',
  invoiced_to_date: '已开票金额', invoiced_amount: '已开票金额',
  collected_amount: '已收款金额', received: '已收款',
  retention_held: '保留款', retention_balance: '保留款余额',
  total_held: '保留款合计', total_released: '已释放保留款', total_adjustment: '调整合计',
  outstanding_amount: '未清金额', uninvoiced_amount: '未开票金额',
  variance: '差异', expected: '预计', linked_amount: '已关联金额',
  standard_cost: '标准成本', margin: '毛利', expected_margin: '预计毛利',
  amount_inc_tax: '含税金额', amount_ex_tax: '未税金额', tax_amount: '税额',
  unit_price: '单价', line_amount: '行金额', completed_amount: '完成金额',
  claimed_amount: '已请款金额', allocated_amount: '已分配金额',
  status: '状态', exception_status: '异常状态',
  remaining_quantity: '剩余数量', contract_quantity: '合同数量',
  cumulative_quantity: '累计数量', approved_quantity: '批准数量',
  item_code: '项目编码', description: '描述', source_description: '原始描述',
  unit: '单位', line_no: '项次', calculation_method: '计算方式',
  variation_no: '变更编号', variation_type: '变更类型',
  deduction_no: '扣款编号', deduction_type: '扣款类型',
  invoice_no: '发票号码', invoice_date: '发票日期',
  receipt_no: '收款编号', receipt_date: '收款日期',
  payment_method: '付款方式', entry_type: '台账类型',
  application_no: '请款编号', period_no: '期数',
  mapping_type: '映射类型', match_method: '匹配方式',
  confidence: '置信度', review_type: '审核类型',
  action: '操作', created_at: '创建时间', updated_at: '更新时间',
  effective_date: '生效日期', approved_at: '批准时间',
  cost_per_unit: '单位成本', total_unit_cost: '单位总成本',
  margin_pct: '毛利率', category: '类别', subcategory: '子类',
};

function labelFor(col: string): string {
  return COLUMN_LABELS[col] || col.replace(/_/g, ' ');
}

function exportCSV(filename: string, rows: Record<string, any>[]) {
  if (rows.length === 0) return;
  const cols = Object.keys(rows[0]);
  const header = cols.map(labelFor).join(',');
  const body = rows.map(row =>
    cols.map(col => {
      const v = row[col];
      if (v === null || v === undefined) return '';
      const s = String(v).replace(/"/g, '""');
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

const PAGE_SIZE = 50;

export default function ReportsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-slate-500">加载中...</div>}>
      <ReportsContent />
    </Suspense>
  );
}

function ReportsContent() {
  const { user, loading } = useAuth();
  const searchParams = useSearchParams();
  const knownReportKeys = reports.map(r => r.key);
  const [activeReport, setActiveReport] = useState<ReportKey>(() => {
    const r = searchParams.get('report');
    return r && knownReportKeys.includes(r as ReportKey) ? (r as ReportKey) : 'project-summary';
  });
  const [data, setData] = useState<Record<string, any>[]>([]);
  const [loadingReport, setLoadingReport] = useState(false);
  const [page, setPage] = useState(1);
  const [contractFilter, setContractFilter] = useState('');

  const refetch = useCallback(() => {
    if (!user) return;
    setLoadingReport(true);
    const url =
      activeReport === 'contract-item-balances' && contractFilter
        ? `/reports/${activeReport}?contract_id=${encodeURIComponent(contractFilter)}`
        : `/reports/${activeReport}`;
    api.get<Record<string, any>[]>(url)
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoadingReport(false));
  }, [user, activeReport, contractFilter]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  useEffect(() => {
    setPage(1);
    setContractFilter('');
  }, [activeReport]);

  if (loading) return null;

  const columns = data.length > 0 ? Object.keys(data[0]) : [];
  const totalPages = Math.max(1, Math.ceil(data.length / PAGE_SIZE));
  const pagedData = data.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const activeEntry = reports.find(r => r.key === activeReport);

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
                  {r.comingSoon && <span className="ml-auto text-xs text-slate-400">规划中</span>}
                </button>
              ))}
            </div>
          </Card>
        </div>

        <div className="lg:col-span-3">
          <Card>
            <CardHeader
              title={activeEntry?.label || ''}
              actions={
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-400">{data.length} 条记录</span>
                  {!activeEntry?.comingSoon && data.length > 0 && (
                    <button
                      onClick={() => exportCSV(`${activeReport}.csv`, data)}
                      className="btn-secondary text-sm px-3 py-1.5"
                    >
                      导出 Excel
                    </button>
                  )}
                </div>
              }
            />
            {activeEntry?.comingSoon ? (
              <EmptyState message="该报表待后端视图实现（Phase C+）" />
            ) : (
              <>
                {activeReport === 'contract-item-balances' && (
                  <div className="mb-3 flex items-center gap-2">
                    <label className="text-xs text-slate-500">合同 ID 过滤:</label>
                    <input
                      type="text"
                      placeholder="可选合同 UUID"
                      value={contractFilter}
                      onChange={e => setContractFilter(e.target.value)}
                      className="input-field text-sm py-1.5 w-80"
                    />
                    <button onClick={() => { setPage(1); refetch(); }} className="btn-primary text-sm px-3 py-1.5">应用</button>
                  </div>
                )}
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
                            <th key={col}>{labelFor(col)}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {pagedData.map((row, i) => {
                          const isOverclaim =
                            activeReport === 'contract-item-balances' &&
                            parseFloat(String(row.remaining_quantity || '0')) < 0;
                          return (
                            <tr key={i} className={isOverclaim ? 'bg-red-50' : ''}>
                              {columns.map((col) => {
                                const val = row[col];
                                const lowerCol = col.toLowerCase();
                                const isMoney = MONEY_HINTS.some(s => lowerCol.includes(s));
                                const isStatus = lowerCol === 'status' || lowerCol.endsWith('_status');
                                const isUuid = lowerCol.endsWith('_id');
                                const isDate = lowerCol.endsWith('_date') || lowerCol.endsWith('_at') || lowerCol === 'created_at';
                                const isException = lowerCol === 'exception_status';
                                if (isException) {
                                  return <td key={col}><StatusBadge status={String(val || 'none')} /></td>;
                                }
                                if (isStatus) return <td key={col}><StatusBadge status={String(val || '—')} /></td>;
                                if (isMoney) return <td key={col} className="num">{val === null || val === undefined ? '—' : formatMoney(val)}</td>;
                                if (isUuid) {
                                  const s = String(val || '');
                                  return <td key={col} title={s} className="font-mono text-xs">{s ? s.substring(0, 8) + '…' : '—'}</td>;
                                }
                                if (isDate) {
                                  const s = String(val || '');
                                  const formatted = s ? s.substring(0, 16).replace('T', ' ') : '';
                                  return <td key={col} className="text-sm text-slate-600">{formatted || '—'}</td>;
                                }
                                const s = String(val ?? '');
                                return <td key={col} className="text-sm text-slate-700">{s.length > 50 ? s.substring(0, 50) + '…' : s || '—'}</td>;
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}
                </div>
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-3 px-2">
                    <span className="text-xs text-slate-400">{data.length} 条 · 第 {page}/{totalPages} 页</span>
                    <div className="flex gap-1">
                      <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="btn-secondary px-3 py-1 text-sm disabled:opacity-40">上一页</button>
                      <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)} className="btn-secondary px-3 py-1 text-sm disabled:opacity-40">下一页</button>
                    </div>
                  </div>
                )}
              </>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
