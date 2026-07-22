'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Project, Contract, ContractItem, Application, ApplicationTotals } from '@/lib/types';
import { useRouter } from 'next/navigation';
import { PageHeader, Card, CardHeader, formatMoney, formatNumber } from '@/components/ui/common';

const STEPS = ['选择项目', '选择合同', '请款信息', '输入数量'] as const;

export default function NewApplicationPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [items, setItems] = useState<ContractItem[]>([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [selectedContract, setSelectedContract] = useState('');
  const [appNo, setAppNo] = useState('');
  const [periodNo, setPeriodNo] = useState(1);
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [applicationDate, setApplicationDate] = useState('');
  const [lines, setLines] = useState<{ itemId: string; qty: string }[]>([]);
  const [preview, setPreview] = useState<ApplicationTotals | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) api.get<Project[]>('/projects').then(setProjects);
  }, [user]);

  useEffect(() => {
    if (selectedProject) api.get<Contract[]>(`/contracts?project_id=${selectedProject}`).then(setContracts);
    else setContracts([]);
  }, [selectedProject]);

  useEffect(() => {
    if (selectedContract) {
      const contract = contracts.find(c => c.id === selectedContract);
      if (contract?.active_version_id) {
        api.get<ContractItem[]>(`/contracts/contract-versions/${contract.active_version_id}/items`).then(setItems);
      }
    } else {
      setItems([]);
    }
  }, [selectedContract, contracts]);

  const computePreview = async () => {
    const filled = lines.filter(l => l.qty && parseFloat(l.qty) > 0);
    if (filled.length === 0 || !selectedContract) { setPreview(null); return; }
    setPreviewLoading(true);
    try {
      const contract = contracts.find(c => c.id === selectedContract)!;
      const taxRate = parseFloat(contract.tax_rate || '0') / 100;
      let gross = 0;
      for (const line of filled) {
        const item = items.find(i => i.id === line.itemId);
        if (!item) continue;
        gross += parseFloat(item.unit_price) * parseFloat(line.qty);
      }
      const retention = gross * 0.05;
      const taxable = gross - retention;
      const tax = taxable * taxRate;
      const invoice = taxable + tax;
      setPreview({
        gross_completed_amount: gross,
        retention_held_amount: retention,
        retention_released_amount: 0,
        deduction_amount: 0,
        taxable_amount: taxable,
        tax_amount: tax,
        invoice_amount: invoice,
      });
    } catch {
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(computePreview, 300);
    return () => clearTimeout(t);
  }, [lines, items, selectedContract, contracts]);

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  const handleCreate = async () => {
    setSubmitting(true);
    try {
      const contract = contracts.find(c => c.id === selectedContract)!;
      void contract;
      const today = applicationDate || new Date().toISOString().slice(0, 10);
      const pStart = periodStart || today;
      const pEnd = periodEnd || today;
      const app = await api.post<Application>('/payment-applications', {
        project_id: selectedProject, contract_id: selectedContract,
        application_no: appNo, period_no: periodNo,
        period_start: pStart, period_end: pEnd, application_date: today,
      });
      for (const line of lines) {
        if (line.qty && parseFloat(line.qty) > 0) {
          await api.post(`/payment-applications/${app.id}/lines`, {
            contract_item_id: line.itemId, current_claimed_quantity: line.qty, current_approved_quantity: line.qty,
          });
        }
      }
      router.push(`/applications/${app.id}`);
    } catch (e) {
      alert(`提交失败：${(e as Error).message}`);
      setSubmitting(false);
    }
  };

  const currentStep = !selectedProject ? 0 : !selectedContract ? 1 : !appNo ? 2 : 3;
  const previewBuckets: { label: string; value: string; emphasis?: boolean }[] = preview
    ? [
        { label: '本期完成金额', value: formatMoney(preview.gross_completed_amount) },
        { label: '本期保留款', value: formatMoney(preview.retention_held_amount) },
        { label: '本期释放保留款', value: formatMoney(preview.retention_released_amount) },
        { label: '本期扣款', value: formatMoney(preview.deduction_amount) },
        { label: '本期未税可开票金额', value: formatMoney(preview.taxable_amount) },
        { label: '税额', value: formatMoney(preview.tax_amount) },
        { label: '含税发票金额', value: formatMoney(preview.invoice_amount), emphasis: true },
      ]
    : [];

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <PageHeader title="新建请款" subtitle="按步骤选择项目、合同并填写本期数量" />

      <div className="flex items-center mb-6">
        {STEPS.map((s, i) => {
          const done = i < currentStep;
          const active = i === currentStep;
          return (
            <div key={s} className="flex items-center flex-1 last:flex-none">
              <div className="flex items-center gap-2">
                <div className={`w-7 h-7 flex items-center justify-center rounded-full text-xs font-semibold border ${done ? 'bg-orange-500 text-white border-orange-500' : active ? 'bg-white text-orange-600 border-orange-500' : 'bg-white text-slate-400 border-slate-300'}`}>
                  {done ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : i + 1}
                </div>
                <span className={`text-sm ${active ? 'font-semibold text-slate-800' : done ? 'text-slate-600' : 'text-slate-400'}`}>{s}</span>
              </div>
              {i < STEPS.length - 1 && <div className={`flex-1 h-px mx-3 ${done ? 'bg-orange-400' : 'bg-slate-200'}`} />}
            </div>
          );
        })}
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader title="选择项目" actions={<span className="text-xs text-slate-400">步骤 1</span>} />
          <div className="card-body">
            <select
              value={selectedProject}
              onChange={e => { setSelectedProject(e.target.value); setSelectedContract(''); }}
              className="select-field"
            >
              <option value="">请选择项目...</option>
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.internal_project_code} - {p.project_name}</option>
              ))}
            </select>
          </div>
        </Card>

        <Card className={selectedProject ? '' : 'opacity-60 pointer-events-none'}>
          <CardHeader title="选择合同" actions={<span className="text-xs text-slate-400">步骤 2</span>} />
          <div className="card-body">
            <select
              value={selectedContract}
              onChange={e => setSelectedContract(e.target.value)}
              className="select-field"
              disabled={!selectedProject}
            >
              <option value="">请选择合同...</option>
              {contracts.map(c => (
                <option key={c.id} value={c.id}>{c.external_contract_no} - {c.contract_name}</option>
              ))}
            </select>
          </div>
        </Card>

        <Card className={selectedContract ? '' : 'opacity-60 pointer-events-none'}>
          <CardHeader title="请款信息" actions={<span className="text-xs text-slate-400">步骤 3</span>} />
          <div className="card-body space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">请款编号</label>
                <input
                  value={appNo}
                  onChange={e => setAppNo(e.target.value)}
                  className="input-field"
                  placeholder="如：25-032-P3"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">期数</label>
                <input
                  type="number"
                  value={periodNo}
                  onChange={e => setPeriodNo(parseInt(e.target.value) || 1)}
                  className="input-field"
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">开始日期</label>
                <input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} className="input-field" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">结束日期</label>
                <input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} className="input-field" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">申请日期</label>
                <input type="date" value={applicationDate} onChange={e => setApplicationDate(e.target.value)} className="input-field" />
              </div>
            </div>
          </div>
        </Card>

        <Card className={selectedContract ? '' : 'opacity-60 pointer-events-none'}>
          <CardHeader title="输入数量" actions={<span className="text-xs text-slate-400">步骤 4</span>} />
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>项次</th>
                  <th>项目名称</th>
                  <th>单位</th>
                  <th className="num">合同数量</th>
                  <th className="num">合同单价</th>
                  <th className="num">本期数量</th>
                </tr>
              </thead>
              <tbody>
                {items.filter(i => i.is_billable && !i.is_heading).map(item => {
                  const line = lines.find(l => l.itemId === item.id);
                  return (
                    <tr key={item.id}>
                      <td className="font-mono text-slate-500">{item.line_no}</td>
                      <td>{item.source_description}</td>
                      <td>{item.unit || '—'}</td>
                      <td className="num">{formatNumber(item.contract_quantity)}</td>
                      <td className="num">{formatMoney(item.unit_price)}</td>
                      <td className="num">
                        <input
                          type="number"
                          step="0.0001"
                          value={line?.qty || ''}
                          onChange={e => {
                            const newLines = [...lines];
                            const existing = newLines.findIndex(l => l.itemId === item.id);
                            if (existing >= 0) newLines[existing].qty = e.target.value;
                            else newLines.push({ itemId: item.id, qty: e.target.value });
                            setLines(newLines);
                          }}
                          className="w-28 px-2 py-1 text-right border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 font-mono tabular-nums"
                        />
                      </td>
                    </tr>
                  );
                })}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400 text-sm">
                      {selectedContract ? '该合同无可计价项目' : '请先选择合同'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <CardHeader title="金额预览" actions={<span className="text-xs text-slate-400">实时计算</span>} />
          <div className="card-body">
            {!preview && !previewLoading && (
              <p className="text-sm text-slate-400 text-center py-4">填写本期数量后将自动计算金额</p>
            )}
            {previewLoading && (
              <p className="text-sm text-slate-400 text-center py-4">计算中...</p>
            )}
            {preview && !previewLoading && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-4">
                {previewBuckets.map(b => (
                  <div key={b.label} className={b.emphasis ? 'col-span-2 md:col-span-1 bg-orange-50 -mx-2 px-3 py-2 rounded-md' : ''}>
                    <p className="text-xs text-slate-500">{b.label}</p>
                    <p className={`mt-0.5 font-mono tabular-nums text-right ${b.emphasis ? 'text-lg font-bold text-orange-600' : 'text-sm font-semibold text-slate-800'}`}>
                      {b.value}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={handleCreate}
            disabled={!appNo || !selectedContract || submitting}
            className="btn-primary"
          >
            {submitting ? '提交中...' : '提交请款'}
          </button>
        </div>
      </div>
    </main>
  );
}
