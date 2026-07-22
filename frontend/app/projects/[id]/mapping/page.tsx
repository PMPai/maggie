'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Contract, ContractItem, ItemMapping, StandardItem } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState, formatNumber } from '@/components/ui/common';

export default function MappingPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [contractItems, setContractItems] = useState<ContractItem[]>([]);
  const [mappings, setMappings] = useState<ItemMapping[]>([]);
  const [standardItems, setStandardItems] = useState<StandardItem[]>([]);

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

  const handleApprove = async (id: string) => {
    try {
      const updated = await api.post<ItemMapping>(`/item-mappings/${id}/approve`, {});
      setMappings(mappings.map(m => (m.id === id ? updated : m)));
    } catch (e) {
      alert(`审批失败：${(e as Error).message}`);
    }
  };

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader title="映射审批" />

      <Card>
        <CardHeader title="映射关系" />
        <div className="card-body">
          {mappings.length === 0 ? (
            <EmptyState message="暂无映射记录" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>合同项目</th>
                  <th>标准项目</th>
                  <th>映射类型</th>
                  <th>匹配方式</th>
                  <th>单位兼容</th>
                  <th>状态</th>
                  <th className="text-right">置信度</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {mappings.map(m => {
                  const ci = contractItemMap.get(m.contract_item_id);
                  const si = standardMap.get(m.standard_item_id);
                  const unitCompatible = ci?.unit && si?.unit
                    ? ci.unit.trim().toLowerCase() === si.unit.trim().toLowerCase()
                    : null;
                  return (
                    <tr key={m.id}>
                      <td>{ci?.source_description || m.contract_item_id.slice(0, 8)}</td>
                      <td>{si?.name || m.standard_item_id.slice(0, 8)}</td>
                      <td>{m.mapping_type}</td>
                      <td>{m.match_method}</td>
                      <td>
                        {unitCompatible === null ? (
                          <span className="text-slate-400">—</span>
                        ) : unitCompatible ? (
                          <span className="badge badge-green">兼容</span>
                        ) : (
                          <span className="badge badge-red">不兼容</span>
                        )}
                      </td>
                      <td><StatusBadge status={m.status} /></td>
                      <td className="num">{formatNumber(m.confidence * 100)}%</td>
                      <td>
                        {m.status === 'PENDING' && (
                          <button onClick={() => handleApprove(m.id)} className="text-orange-600 hover:underline text-sm">
                            批准
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </main>
  );
}
