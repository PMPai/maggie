'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Project, Contract, ContractItem, Application, ApplicationLine, ApplicationTotals } from '@/lib/types';
import { useRouter } from 'next/navigation';

export default function NewApplicationPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(1);
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

  useEffect(() => {
    if (user) api.get<Project[]>('/projects').then(setProjects);
  }, [user]);

  useEffect(() => {
    if (selectedProject) api.get<Contract[]>(`/contracts?project_id=${selectedProject}`).then(setContracts);
  }, [selectedProject]);

  useEffect(() => {
    if (selectedContract) {
      const contract = contracts.find(c => c.id === selectedContract);
      if (contract?.active_version_id) {
        api.get<ContractItem[]>(`/contracts/contract-versions/${contract.active_version_id}/items`).then(setItems);
      }
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
    const contract = contracts.find(c => c.id === selectedContract)!;
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
  };

  const num = (v: number) => Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

  return (
    <main className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">新建请款</h1>
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium mb-1">步骤1：选择项目</label>
          <select value={selectedProject} onChange={e => setSelectedProject(e.target.value)} className="w-full rounded border px-3 py-2">
            <option value="">请选择...</option>
            {projects.map(p => <option key={p.id} value={p.id}>{p.internal_project_code} - {p.project_name}</option>)}
          </select>
        </div>
        {selectedProject && (
          <div>
            <label className="block text-sm font-medium mb-1">步骤2：选择合同</label>
            <select value={selectedContract} onChange={e => setSelectedContract(e.target.value)} className="w-full rounded border px-3 py-2">
              <option value="">请选择...</option>
              {contracts.map(c => <option key={c.id} value={c.id}>{c.external_contract_no} - {c.contract_name}</option>)}
            </select>
          </div>
        )}
        {selectedContract && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">请款编号</label>
                <input value={appNo} onChange={e => setAppNo(e.target.value)} className="w-full rounded border px-3 py-2" placeholder="如：25-032-P3" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">期数</label>
                <input type="number" value={periodNo} onChange={e => setPeriodNo(parseInt(e.target.value))} className="w-full rounded border px-3 py-2" />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">期间开始日期</label>
                <input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} className="w-full rounded border px-3 py-2" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">期间结束日期</label>
                <input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} className="w-full rounded border px-3 py-2" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">申请日期</label>
                <input type="date" value={applicationDate} onChange={e => setApplicationDate(e.target.value)} className="w-full rounded border px-3 py-2" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">步骤3：输入本期数量</label>
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left">项次</th>
                    <th className="px-3 py-2 text-left">项目名称</th>
                    <th className="px-3 py-2 text-left">单位</th>
                    <th className="px-3 py-2 text-right">合同数量</th>
                    <th className="px-3 py-2 text-right">本期数量</th>
                  </tr>
                </thead>
                <tbody>
                  {items.filter(i => i.is_billable && !i.is_heading).map(item => (
                    <tr key={item.id} className="border-t">
                      <td className="px-3 py-2">{item.line_no}</td>
                      <td className="px-3 py-2">{item.source_description}</td>
                      <td className="px-3 py-2">{item.unit}</td>
                      <td className="px-3 py-2 text-right">{Number(item.contract_quantity).toLocaleString()}</td>
                      <td className="px-3 py-2"><input type="number" step="0.0001" className="w-24 rounded border px-2 py-1 text-right" onChange={e => {
                        const newLines = [...lines];
                        const existing = newLines.findIndex(l => l.itemId === item.id);
                        if (existing >= 0) newLines[existing].qty = e.target.value;
                        else newLines.push({ itemId: item.id, qty: e.target.value });
                        setLines(newLines);
                      }} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {preview && (
              <div className="rounded-lg bg-gray-50 p-4">
                <h3 className="text-sm font-semibold mb-3">本期金额预览</h3>
                {previewLoading ? (
                  <p className="text-sm text-gray-500">计算中...</p>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    <div><p className="text-xs text-gray-500">本期完成金额</p><p className="font-bold">{num(preview.gross_completed_amount)}</p></div>
                    <div><p className="text-xs text-gray-500">本期保留款</p><p className="font-bold text-red-600">-{num(preview.retention_held_amount)}</p></div>
                    <div><p className="text-xs text-gray-500">本期释放保留款</p><p className="font-bold text-green-600">{num(preview.retention_released_amount)}</p></div>
                    <div><p className="text-xs text-gray-500">本期扣款</p><p className="font-bold text-red-600">-{num(preview.deduction_amount)}</p></div>
                    <div><p className="text-xs text-gray-500">本期未税可开票金额</p><p className="font-bold">{num(preview.taxable_amount)}</p></div>
                    <div><p className="text-xs text-gray-500">税额</p><p className="font-bold">{num(preview.tax_amount)}</p></div>
                    <div><p className="text-xs text-blue-600">含税发票金额</p><p className="text-lg font-bold text-blue-700">{num(preview.invoice_amount)}</p></div>
                  </div>
                )}
              </div>
            )}

            <button onClick={handleCreate} disabled={!appNo} className="rounded bg-blue-600 px-6 py-2 text-white hover:bg-blue-700 disabled:opacity-50">提交请款</button>
          </>
        )}
      </div>
    </main>
  );
}
