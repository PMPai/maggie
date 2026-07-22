'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Contract, ContractItem, ItemMapping, StandardItem } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function MappingPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [contractItems, setContractItems] = useState<ContractItem[]>([]);
  const [mappings, setMappings] = useState<ItemMapping[]>([]);
  const [standardItems, setStandardItems] = useState<StandardItem[]>([]);
  const [selectedContractItem, setSelectedContractItem] = useState<string>('');
  const [selectedStandardItem, setSelectedStandardItem] = useState<string>('');

  useEffect(() => {
    if (!user) return;
    (async () => {
      const standards = await api.get<StandardItem[]>('/standard-items').catch(() => [] as StandardItem[]);
      setStandardItems(standards);
      const contracts = await api.get<Contract[]>(`/contracts?project_id=${projectId}`).catch(() => [] as Contract[]);
      const allItems: ContractItem[] = [];
      for (const c of contracts) {
        if (c.active_version_id) {
          try {
            const items = await api.get<ContractItem[]>(`/contracts/contract-versions/${c.active_version_id}/items`);
            allItems.push(...items);
          } catch {}
        }
      }
      setContractItems(allItems);
      api.get<ItemMapping[]>(`/item-mappings?project_id=${projectId}`).then(setMappings).catch(() => setMappings([]));
    })();
  }, [user, projectId]);

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  const standardMap = new Map(standardItems.map(s => [s.id, s]));
  const contractItemMap = new Map(contractItems.map(c => [c.id, c]));

  const handleCreateMapping = async () => {
    if (!selectedContractItem || !selectedStandardItem) return;
    try {
      const created = await api.post<ItemMapping>('/item-mappings', {
        contract_item_id: selectedContractItem,
        standard_item_id: selectedStandardItem,
        project_id: projectId,
      });
      setMappings([...mappings, created]);
      setSelectedContractItem('');
      setSelectedStandardItem('');
    } catch (e) {
      alert(`创建映射失败：${(e as Error).message}`);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      const updated = await api.post<ItemMapping>(`/item-mappings/${id}/approve`, {});
      setMappings(mappings.map(m => (m.id === id ? updated : m)));
    } catch (e) {
      alert(`审批失败：${(e as Error).message}`);
    }
  };

  return (
    <main className="p-8 max-w-7xl mx-auto">
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-blue-600 hover:underline">← 返回项目</Link>
      </div>
      <h1 className="text-2xl font-bold mb-6">映射审批</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-lg bg-white shadow p-4">
          <h2 className="text-sm font-semibold mb-3">合同项目</h2>
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr><th className="px-2 py-1 text-left">项次</th><th className="px-2 py-1 text-left">名称</th></tr>
              </thead>
              <tbody>
                {contractItems.filter(i => i.is_billable && !i.is_heading).map(i => (
                  <tr key={i.id} className={`border-t cursor-pointer hover:bg-blue-50 ${selectedContractItem === i.id ? 'bg-blue-100' : ''}`} onClick={() => setSelectedContractItem(i.id)}>
                    <td className="px-2 py-1 font-mono">{i.line_no}</td>
                    <td className="px-2 py-1">{i.source_description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-lg bg-white shadow p-4">
          <h2 className="text-sm font-semibold mb-3">映射关系</h2>
          <div className="mb-3 space-y-2 rounded bg-gray-50 p-2 text-xs">
            <p>已选合同项：{contractItemMap.get(selectedContractItem)?.source_description || '—'}</p>
            <p>已选标准项：{standardMap.get(selectedStandardItem)?.name || '—'}</p>
            <button onClick={handleCreateMapping} disabled={!selectedContractItem || !selectedStandardItem} className="rounded bg-blue-600 px-3 py-1 text-white hover:bg-blue-700 disabled:opacity-50">新建映射</button>
          </div>
          <div className="max-h-80 overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-2 py-1 text-left">合同项</th>
                  <th className="px-2 py-1 text-left">标准项</th>
                  <th className="px-2 py-1 text-left">状态</th>
                  <th className="px-2 py-1 text-left">置信度</th>
                  <th className="px-2 py-1 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {mappings.map(m => {
                  const ci = contractItemMap.get(m.contract_item_id);
                  const si = standardMap.get(m.standard_item_id);
                  return (
                    <tr key={m.id} className="border-t">
                      <td className="px-2 py-1">{ci?.source_description || m.contract_item_id.slice(0, 8)}</td>
                      <td className="px-2 py-1">{si?.name || m.standard_item_id.slice(0, 8)}</td>
                      <td className="px-2 py-1">{m.status}</td>
                      <td className="px-2 py-1">{(m.confidence * 100).toFixed(0)}%</td>
                      <td className="px-2 py-1">{m.status === 'PENDING' && <button onClick={() => handleApprove(m.id)} className="text-blue-600 hover:underline">批准</button>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-lg bg-white shadow p-4">
          <h2 className="text-sm font-semibold mb-3">标准项</h2>
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr><th className="px-2 py-1 text-left">编号</th><th className="px-2 py-1 text-left">名称</th></tr>
              </thead>
              <tbody>
                {standardItems.map(s => (
                  <tr key={s.id} className={`border-t cursor-pointer hover:bg-green-50 ${selectedStandardItem === s.id ? 'bg-green-100' : ''}`} onClick={() => setSelectedStandardItem(s.id)}>
                    <td className="px-2 py-1 font-mono">{s.code}</td>
                    <td className="px-2 py-1">{s.name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
