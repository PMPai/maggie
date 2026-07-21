'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Project, Contract, ContractItem, Application, ApplicationLine } from '@/lib/types';
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
  const [lines, setLines] = useState<{itemId: string; qty: string}[]>([]);

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

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  const handleCreate = async () => {
    const contract = contracts.find(c => c.id === selectedContract)!;
    const app = await api.post<Application>('/payment-applications', {
      project_id: selectedProject, contract_id: selectedContract,
      application_no: appNo, period_no: periodNo,
      period_start: '2026-04-01', period_end: '2026-04-30', application_date: '2026-04-30',
    });
    for (const line of lines) {
      if (line.qty && parseFloat(line.qty) > 0) {
        await api.post(`/payment-applications/${app.id}/lines`, {
          contract_item_id: line.itemId, current_claimed_quantity: line.qty, current_approved_quantity: line.qty,
        });
      }
    }
    router.push(`/projects/${selectedProject}`);
  };

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
            <button onClick={handleCreate} disabled={!appNo} className="rounded bg-blue-600 px-6 py-2 text-white hover:bg-blue-700 disabled:opacity-50">提交请款</button>
          </>
        )}
      </div>
    </main>
  );
}
