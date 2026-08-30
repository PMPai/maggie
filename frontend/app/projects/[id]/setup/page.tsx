'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';
import type { Project } from '@/lib/types';
import { PageHeader, Card, CardHeader, EmptyState, formatMoney } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

type Step = 1 | 2 | 3;
interface BudgetRow {
  line_no: string;
  description: string;
  unit: string;
  quantity: string;
  unit_price: string;
  unit_cost: string;
  expected_payment_date: string;
}

export default function ProjectSetupPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const [project, setProject] = useState<Project | null>(null);
  const [step, setStep] = useState<Step>(1);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [contractId, setContractId] = useState('');
  const [versionId, setVersionId] = useState('');

  // Step 1: pricing sheet form
  const [sheetForm, setSheetForm] = useState({
    contract_name: '计价单',
    external_contract_no: '',
    tax_mode: 'EXCLUSIVE',
    tax_rate: '0.05',
  });

  // Step 2: budget rows (计价单逐项)
  const [rows, setRows] = useState<BudgetRow[]>([
    { line_no: '1', description: '', unit: '', quantity: '', unit_price: '', unit_cost: '', expected_payment_date: '' },
  ]);

  useEffect(() => {
    if (!user) return;
    api.get<Project>(`/projects/${projectId}`).then(setProject).catch(e => setError(e?.message || '加载失败'));
  }, [user, projectId]);

  if (loading) return <PageLoader />;
  if (!project) return <div className="p-8">加载中...</div>;

  const createPricingSheet = async () => {
    if (!sheetForm.contract_name) {
      setError('计价单名称为必填');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const ps = await api.post<{ contract_id: string; version_id: string }>(
        `/contracts/projects/${projectId}/pricing-sheets`,
        {
          contract_name: sheetForm.contract_name,
          external_contract_no: sheetForm.external_contract_no || undefined,
          tax_mode: sheetForm.tax_mode,
          tax_rate: sheetForm.tax_rate,
        }
      );
      setContractId(ps.contract_id);
      setVersionId(ps.version_id);
      setStep(2);
    } catch (e: any) {
      setError(e?.message || '创建计价单失败');
    } finally {
      setBusy(false);
    }
  };

  const addBudgetRow = () => {
    setRows([...rows, { line_no: String(rows.length + 1), description: '', unit: '', quantity: '', unit_price: '', unit_cost: '', expected_payment_date: '' }]);
  };

  const removeBudgetRow = (i: number) => {
    setRows(rows.filter((_, idx) => idx !== i));
  };

  const saveBudgetRows = async () => {
    const validRows = rows.filter(r => r.description && r.quantity);
    if (validRows.length === 0) {
      setError('至少需要一行有效的计价项目（描述+数量）');
      return;
    }
    setBusy(true);
    setError('');
    try {
      for (const r of validRows) {
        const qty = parseFloat(r.quantity) || 0;
        const price = parseFloat(r.unit_price) || 0;
        const cost = parseFloat(r.unit_cost) || 0;
        await api.post(`/contracts/contract-versions/${versionId}/items`, {
          line_no: r.line_no,
          source_description: r.description,
          unit: r.unit || null,
          contract_quantity: String(qty),
          unit_price: String(price),
          unit_cost: cost > 0 ? String(cost) : null,
          line_amount: String(qty * price),
          calculation_method: 'QUANTITY',
          expected_payment_date: r.expected_payment_date || null,
        });
      }
      setStep(3);
    } catch (e: any) {
      setError(e?.message || '保存计价项目失败');
    } finally {
      setBusy(false);
    }
  };

  const submitAndApprove = async () => {
    setBusy(true);
    setError('');
    try {
      await api.post(`/contracts/${contractId}/versions/${versionId}/approve`);
      router.push(`/projects/${projectId}/budget`);
    } catch (e: any) {
      setError(e?.message || '审批失败');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <PageHeader title="计价单设置" subtitle={`${project.internal_project_code} · ${project.project_name}`} />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-6">
        {[
          { n: 1, label: '新建计价单' },
          { n: 2, label: '计价项目' },
          { n: 3, label: '审核通过' },
        ].map((s, i) => (
          <div key={s.n} className="flex items-center gap-2">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
              step >= s.n ? 'bg-orange-100 text-orange-700' : 'bg-slate-100 text-slate-400'
            }`}>
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${
                step > s.n ? 'bg-green-500 text-white' : step === s.n ? 'bg-orange-500 text-white' : 'bg-slate-300 text-white'
              }`}>
                {step > s.n ? '✓' : s.n}
              </span>
              {s.label}
            </div>
            {i < 2 && <span className="text-slate-300">→</span>}
          </div>
        ))}
      </div>

      {/* Step 1: Pricing sheet */}
      {step === 1 && (
        <Card>
          <CardHeader title="新建计价单" />
          <div className="card-body grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">计价单名称 *</label>
              <input type="text" value={sheetForm.contract_name}
                onChange={e => setSheetForm({...sheetForm, contract_name: e.target.value})}
                className="input-field text-sm" placeholder="例如 污水工作井地改工程" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">编号（选填）</label>
              <input type="text" value={sheetForm.external_contract_no}
                onChange={e => setSheetForm({...sheetForm, external_contract_no: e.target.value})}
                className="input-field text-sm" placeholder="自动生成或手动填写" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">税务模式</label>
              <select value={sheetForm.tax_mode}
                onChange={e => setSheetForm({...sheetForm, tax_mode: e.target.value})}
                className="input-field text-sm">
                <option value="EXCLUSIVE">未税</option>
                <option value="INCLUSIVE">含税</option>
                <option value="MIXED">混合</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">税率</label>
              <input type="text" value={sheetForm.tax_rate}
                onChange={e => setSheetForm({...sheetForm, tax_rate: e.target.value})}
                className="input-field text-sm" />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button onClick={createPricingSheet} disabled={busy} className="btn-primary">
              {busy ? '创建中...' : '下一步：添加计价项目'}
            </button>
          </div>
        </Card>
      )}

      {/* Step 2: Budget rows (计价单逐项) */}
      {step === 2 && (
        <Card>
          <CardHeader title="计价单逐项编辑" actions={
            <button onClick={addBudgetRow} className="btn-secondary text-sm">+ 添加行</button>
          } />
          <div className="overflow-x-auto">
            <table className="data-table text-xs">
              <thead>
                <tr>
                  <th>项次</th><th>名称</th><th>单位</th>
                  <th className="text-right">数量</th><th className="text-right">单价</th>
                  <th className="text-right">单位成本</th>
                  <th className="text-right">金额</th><th>付款时间</th><th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td><input value={r.line_no} onChange={e => { const c=[...rows]; c[i]={...r, line_no: e.target.value}; setRows(c); }} className="input-field text-xs w-12" /></td>
                    <td><input value={r.description} onChange={e => { const c=[...rows]; c[i]={...r, description: e.target.value}; setRows(c); }} className="input-field text-xs w-full" placeholder="项目名称" /></td>
                    <td><input value={r.unit} onChange={e => { const c=[...rows]; c[i]={...r, unit: e.target.value}; setRows(c); }} className="input-field text-xs w-16" /></td>
                    <td><input type="number" value={r.quantity} onChange={e => { const c=[...rows]; c[i]={...r, quantity: e.target.value}; setRows(c); }} className="input-field text-xs w-20" /></td>
                    <td><input type="number" value={r.unit_price} onChange={e => { const c=[...rows]; c[i]={...r, unit_price: e.target.value}; setRows(c); }} className="input-field text-xs w-20" /></td>
                    <td><input type="number" value={r.unit_cost} onChange={e => { const c=[...rows]; c[i]={...r, unit_cost: e.target.value}; setRows(c); }} className="input-field text-xs w-20" /></td>
                    <td className="num">{formatMoney((parseFloat(r.quantity)||0) * (parseFloat(r.unit_price)||0))}</td>
                    <td><input type="date" value={r.expected_payment_date} onChange={e => { const c=[...rows]; c[i]={...r, expected_payment_date: e.target.value}; setRows(c); }} className="input-field text-xs w-32" /></td>
                    <td><button onClick={() => removeBudgetRow(i)} className="text-red-400 hover:text-red-600 text-xs">删除</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex justify-end">
            <button onClick={saveBudgetRows} disabled={busy} className="btn-primary">
              {busy ? '保存中...' : '下一步：审核通过'}
            </button>
          </div>
        </Card>
      )}

      {/* Step 3: Submit + approve */}
      {step === 3 && (
        <Card>
          <CardHeader title="审核通过 → 转为合同" />
          <div className="card-body">
            <p className="text-sm text-slate-600 mb-4">
              计价单与逐项已保存。点击下方按钮审核通过，计价单将转为正式合同（SIGNED_CONTRACT），
              系统将自动依付款时间生成应收款计划（PLANNED 收款单）。
            </p>
            <button onClick={submitAndApprove} disabled={busy} className="btn-primary">
              {busy ? '处理中...' : '审核通过 → 跳转 Master Budget'}
            </button>
          </div>
        </Card>
      )}
    </main>
  );
}
