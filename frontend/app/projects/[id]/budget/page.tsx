'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { MasterBudgetResponse, MasterBudgetRow } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, EmptyState, formatMoney, formatNumber } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

export default function MasterBudgetPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [data, setData] = useState<MasterBudgetResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    api.get<MasterBudgetResponse>(`/projects/${projectId}/master-budget`)
      .then(setData)
      .catch(e => setError(e?.message || '加载失败'));
  }, [user, projectId]);

  const rows = data?.rows ?? [];

  const idToDepth = useMemo(() => {
    const map: Record<string, number> = {};
    const byId = new Map(rows.map(r => [r.contract_item_id, r]));
    const compute = (row: MasterBudgetRow): number => {
      if (map[row.contract_item_id] !== undefined) return map[row.contract_item_id];
      if (!row.parent_item_id) {
        map[row.contract_item_id] = 0;
        return 0;
      }
      const parent = byId.get(row.parent_item_id);
      const depth = parent ? compute(parent) + 1 : 0;
      map[row.contract_item_id] = depth;
      return depth;
    };
    rows.forEach(compute);
    return map;
  }, [rows]);

  const totals = useMemo(() => rows.reduce((acc, r) => {
    acc.completed += parseFloat(r.completed_amount || '0');
    acc.retention += parseFloat(r.retention_balance || '0');
    acc.claimed += parseFloat(r.claimed_amount || '0');
    acc.invoiced += parseFloat(r.invoiced_amount || '0');
    acc.collected += parseFloat(r.collected_amount || '0');
    return acc;
  }, { completed: 0, retention: 0, claimed: 0, invoiced: 0, collected: 0 }), [rows]);

  if (loading) return <PageLoader message="加载 Master Budget..." />;
  if (!user) return <div className="p-8">请先登录</div>;
  if (!data && !error) return <PageLoader message="加载 Master Budget..." />;

  return (
    <main className="p-8 max-w-7xl mx-auto">
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader title="Master Budget" subtitle="合同预算 vs 累计 vs 成本毛利" />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      <Card>
        <CardHeader
          title="明细"
          actions={<span className="text-xs text-slate-400">{rows.length} 行</span>}
        />
        <div className="card-body">
          {rows.length === 0 ? (
            <EmptyState message="暂无合同项目" />
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table text-xs">
                <thead>
                  <tr>
                    <th>项次</th>
                    <th>项目名称</th>
                    <th>单位</th>
                    <th className="text-right">合同数量</th>
                    <th className="text-right">合同单价</th>
                    <th className="text-right">标准单价</th>
                    <th className="text-right">价差</th>
                    <th className="text-right">变更</th>
                    <th className="text-right">累计批准</th>
                    <th className="text-right">剩余</th>
                    <th className="text-right">完成金额</th>
                    <th className="text-right">毛利</th>
                    <th className="text-right">毛利率</th>
                    <th>预期支付</th>
                    <th>实际支付</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(r => {
                    const depth = idToDepth[r.contract_item_id] ?? 0;
                    const rowBg = r.exception_status === 'overclaim'
                      ? 'bg-red-50'
                      : r.exception_status === 'unmapped'
                        ? 'bg-slate-50'
                        : '';
                    const remaining = parseFloat(r.remaining_quantity);
                    const priceVar = r.price_variance ? parseFloat(r.price_variance) : null;
                    return (
                      <tr key={r.contract_item_id} className={rowBg}>
                        <td className="font-mono whitespace-nowrap">{r.line_no}</td>
                        <td style={{ paddingLeft: `${depth * 16 + 8}px` }}>{r.description}</td>
                        <td>{r.unit || '—'}</td>
                        <td className="num">{formatNumber(r.contract_quantity)}</td>
                        <td className="num">{formatMoney(r.unit_price)}</td>
                        <td className="num">{r.standard_cost_per_unit ? formatMoney(r.standard_cost_per_unit) : '—'}</td>
                        <td className="num">
                          {priceVar !== null ? (
                            <span className={priceVar < 0 ? 'text-red-600' : 'text-green-600'}>{formatMoney(r.price_variance)}</span>
                          ) : '—'}
                        </td>
                        <td className="num">{formatNumber(r.variation_delta)}</td>
                        <td className="num">{formatNumber(r.cumulative_approved_quantity)}</td>
                        <td className="num">
                          {!isNaN(remaining) && remaining < 0 ? (
                            <span className="text-red-600 font-semibold">{formatNumber(r.remaining_quantity)}</span>
                          ) : formatNumber(r.remaining_quantity)}
                        </td>
                        <td className="num">{formatMoney(r.completed_amount)}</td>
                        <td className="num">{r.expected_margin ? formatMoney(r.expected_margin) : '—'}</td>
                        <td className="num">{r.margin_pct ? parseFloat(r.margin_pct).toFixed(1) + '%' : '—'}</td>
                        <td className="text-xs text-slate-600 whitespace-nowrap">{r.expected_payment_date || '—'}</td>
                        <td className="text-xs text-slate-600 whitespace-nowrap">{r.actual_payment_date || '—'}</td>
                        <td>
                          {r.exception_status === 'overclaim' ? (
                            <span className="badge badge-red">超量</span>
                          ) : r.exception_status === 'unmapped' ? (
                            <span className="badge badge-gray">未映射</span>
                          ) : (
                            <span className="badge badge-green">正常</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="font-semibold bg-slate-50">
                    <td colSpan={10} className="text-right">合计</td>
                    <td className="num">{formatMoney(totals.completed)}</td>
                    <td colSpan={5}></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </div>
      </Card>
    </main>
  );
}
