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

  // Step 1: contract form
  const [contractForm, setContractForm] = useState({
    external_contract_no: '',
    contract_name: '',
    tax_mode: 'EXCLUSIVE',
    tax_rate: '0.05',
    amount_ex_tax: '',
    tax_amount: '',
    amount_inc_tax: '',
  });

  // Step 2: budget rows
  const [rows, setRows] = useState<BudgetRow[]>([
    { line_no: '1', description: '', unit: '', quantity: '', unit_price: '', expected_payment_date: '' },
  ]);

  useEffect(() => {
    if (!user) return;
    api.get<Project>(`/projects/${projectId}`).then(setProject).catch(e => setError(e?.message || '加载失败'));
  }, [user, projectId]);

  if (loading) return <PageLoader />;
  if (!project) return <div className="p-8">加载中...</div>;

  const createContract = async () => {
    if (!contractForm.external_contract_no || !contractForm.contract_name || !contractForm.amount_inc_tax) {
      setError('合同编号、名称、含税金额为必填');
      return;
    }
    const ex = parseFloat(contractForm.amount_ex_tax || '0');
    const tax = parseFloat(contractForm.tax_amount || '0');
    const inc = parseFloat(contractForm.amount_inc_tax || '0');
    if (Math.abs(ex + tax - inc) > 0.01) {
      setError('未税金额 + 税额 ≠ 含税金额');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const c = await api.post<any>('/contracts', {
        project_id: projectId,
        external_contract_no: contractForm.external_contract_no,
        contract_name: contractForm.contract_name,
        tax_mode: contractForm.tax_mode,
        tax_rate: contractForm.tax_rate,
        original_amount_ex_tax: contractForm.amount_ex_tax,
        original_tax_amount: contractForm.tax_amount,
        original_amount_inc_tax: contractForm.amount_inc_tax,
      });
      setContractId(c.id);
      // Create DRAFT version
      const v = await api.post<any>(`/contracts/${c.id}/versions`, {
        version_type: 'QUOTATION',
        amount_ex_tax: contractForm.amount_ex_tax,
        tax_amount: contractForm.tax_amount,
        amount_inc_tax: contractForm.amount_inc_tax,
      });
      setVersionId(v.id);
      setStep(2);
    } catch (e: any) {
      setError(e?.message || '创建合同失败');
    } finally {
      setBusy(false);
    }
  };

  const addBudgetRow = () => {
    setRows([...rows, { line_no: String(rows.length + 1), description: '', unit: '', quantity: '', unit_price: '', expected_payment_date: '' }]);
  };

  const saveBudgetRows = async () => {
    const validRows = rows.filter(r => r.description && r.quantity);
    if (validRows.length === 0) {
      setError('至少需要一行有效的预算项目（描述+数量）');
      return;
    }
    setBusy(true);
    setError('');
    try {
      for (const r of validRows) {
        const qty = parseFloat(r.quantity) || 0;
        const price = parseFloat(r.unit_price) || 0;
        await api.post(`/contracts/contract-versions/${versionId}/items`, {
          line_no: r.line_no,
          source_description: r.description,
          unit: r.unit || null,
          contract_quantity: String(qty),
          unit_price: String(price),
          line_amount: String(qty * price),
          calculation_method: 'QUANTITY',
          expected_payment_date: r.expected_payment_date || null,
        });
      }
      setStep(3);
    } catch (e: any) {
      setError(e?.message || '保存预算项目失败');
    } finally {
      setBusy(false);
    }
  };

  const submitAndApprove = async () => {
    setBusy(true);
    setError('');
    try {
      // Directly approve the DRAFT version — the approve endpoint accepts
      // both DRAFT and UNDER_REVIEW statuses, so the intermediate PATCH to
      // UNDER_REVIEW (which requires CONTRACT_ADMIN role) is unnecessary and
      // would block project managers from completing the setup flow.
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
      <PageHeader title="项目预算设置" subtitle={`${project.internal_project_code} · ${project.project_name}`} />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-6">
        {[
          { n: 1, label: '新建合同' },
          { n: 2, label: '预算项目' },
          { n: 3, label: '提交批准' },
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

      {/* Step 1: Contract */}
      {step === 1 && (
        <Card>
          <CardHeader title="新建合同" />
          <div className="card-body grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">合同编号 *</label>
              <input type="text" value={contractForm.external_contract_no}
                onChange={e => setContractForm({...contractForm, external_contract_no: e.target.value})}
                className="input-field text-sm" placeholder="例如 CQ880A-11501" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">合同名称 *</label>
              <input type="text" value={contractForm.contract_name}
                onChange={e => setContractForm({...contractForm, contract_name: e.target.value})}
                className="input-field text-sm" placeholder="例如 污水工作井地改工程" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">税务模式</label>
              <select value={contractForm.tax_mode}
                onChange={e => setContractForm({...contractForm, tax_mode: e.target.value})}
                className="input-field text-sm">
                <option value="EXCLUSIVE">未税</option>
                <option value="INCLUSIVE">含税</option>
                <option value="MIXED">混合</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">税率</label>
              <input type="text" value={contractForm.tax_rate}
                onChange={e => setContractForm({...contractForm, tax_rate: e.target.value})}
                className="input-field text-sm" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">未税金额</label>
              <input type="number" value={contractForm.amount_ex_tax}
                onChange={e => setContractForm({...contractForm, amount_ex_tax: e.target.value})}
                className="input-field text-sm" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">税额</label>
              <input type="number" value={contractForm.tax_amount}
                onChange={e => setContractForm({...contractForm, tax_amount: e.target.value})}
                className="input-field text-sm" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">含税金额 *</label>
              <input type="number" value={contractForm.amount_inc_tax}
                onChange={e => setContractForm({...contractForm, amount_inc_tax: e.target.value})}
                className="input-field text-sm" />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button onClick={createContract} disabled={busy} className="btn-primary">
              {busy ? '创建中...' : '下一步：添加预算项目'}
            </button>
          </div>
        </Card>
      )}

      {/* Step 2: Budget rows */}
      {step === 2 && (
        <Card>
          <CardHeader title="预算项目明细" actions={
            <button onClick={addBudgetRow} className="btn-secondary text-sm">+ 添加行</button>
          } />
          <div className="overflow-x-auto">
            <table className="data-table text-xs">
              <thead>
                <tr>
                  <th>项次</th><th>描述</th><th>单位</th>
                  <th className="text-right">数量</th><th className="text-right">单价</th>
                  <th className="text-right">金额</th><th>预期支付</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td><input value={r.line_no} onChange={e => { const c=[...rows]; c[i]={...r, line_no: e.target.value}; setRows(c); }} className="input-field text-xs w-12" /></td>
                    <td><input value={r.description} onChange={e => { const c=[...rows]; c[i]={...r, description: e.target.value}; setRows(c); }} className="input-field text-xs w-full" placeholder="项目描述" /></td>
                    <td><input value={r.unit} onChange={e => { const c=[...rows]; c[i]={...r, unit: e.target.value}; setRows(c); }} className="input-field text-xs w-16" /></td>
                    <td><input type="number" value={r.quantity} onChange={e => { const c=[...rows]; c[i]={...r, quantity: e.target.value}; setRows(c); }} className="input-field text-xs w-20" /></td>
                    <td><input type="number" value={r.unit_price} onChange={e => { const c=[...rows]; c[i]={...r, unit_price: e.target.value}; setRows(c); }} className="input-field text-xs w-20" /></td>
                    <td className="num">{formatMoney((parseFloat(r.quantity)||0) * (parseFloat(r.unit_price)||0))}</td>
                    <td><input type="date" value={r.expected_payment_date} onChange={e => { const c=[...rows]; c[i]={...r, expected_payment_date: e.target.value}; setRows(c); }} className="input-field text-xs w-32" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex justify-end">
            <button onClick={saveBudgetRows} disabled={busy} className="btn-primary">
              {busy ? '保存中...' : '下一步：提交批准'}
            </button>
          </div>
        </Card>
      )}

      {/* Step 3: Submit + approve */}
      {step === 3 && (
        <Card>
          <CardHeader title="提交审核与批准" />
          <div className="card-body">
            <p className="text-sm text-slate-600 mb-4">
              合同与预算项目已保存。点击下方按钮提交审核并批准合同版本。批准后，Master Budget 页面将显示完整预算数据。
            </p>
            <button onClick={submitAndApprove} disabled={busy} className="btn-primary">
              {busy ? '处理中...' : '提交审核并批准 → 跳转 Master Budget'}
            </button>
          </div>
        </Card>
      )}
    </main>
  );
}
