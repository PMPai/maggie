'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import type { Contract, ContractItem, ItemMapping, StandardItem } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState, formatNumber } from '@/components/ui/common';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

export default function MappingPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [contractItems, setContractItems] = useState<ContractItem[]>([]);
  const [mappings, setMappings] = useState<ItemMapping[]>([]);
  const [standards, setStandards] = useState<StandardItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<ContractItem | null>(null);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    (async () => {
      const stds = await api.get<StandardItem[]>('/standard-items').catch(() => [] as StandardItem[]);
      setStandards(stds);
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

  const standardMap = useMemo(() => new Map(standards.map(s => [s.id, s])), [standards]);
  const mappingByItem = useMemo(() => {
    const m = new Map<string, ItemMapping>();
    mappings.forEach(mp => m.set(mp.contract_item_id, mp));
    return m;
  }, [mappings]);

  const filteredStandards = useMemo(() => {
    if (!search) return standards.slice(0, 10);
    const s = search.toLowerCase();
    return standards.filter(st => st.code.toLowerCase().includes(s) || st.name.toLowerCase().includes(s)).slice(0, 20);
  }, [standards, search]);

  const handleCreateMapping = async (standardItemId: string) => {
    if (!selectedItem) return;
    setBusy(true); setError('');
    try {
      const newMap = await api.post<ItemMapping>('/item-mappings', {
        project_id: projectId,
        contract_item_id: selectedItem.id,
        standard_item_id: standardItemId,
        mapping_type: 'ONE_TO_ONE',
        match_method: 'MANUAL',
        unit_compatibility: selectedItem.unit === standardMap.get(standardItemId)?.unit ? 'SAME' : 'UNKNOWN',
        confidence: 1.0,
        status: 'PENDING_REVIEW',
      });
      setMappings([...mappings, newMap]);
      setError('映射已创建，待审批');
    } catch (e: any) { setError(e?.message || '创建失败'); }
    finally { setBusy(false); }
  };

  const handleApprove = async (mappingId: string) => {
    setBusy(true); setError('');
    try {
      const updated = await api.post<ItemMapping>(`/item-mappings/${mappingId}/approve`, {});
      setMappings(mappings.map(m => m.id === mappingId ? updated : m));
    } catch (e: any) { setError(e?.message || '审批失败'); }
    finally { setBusy(false); }
  };

  const handleReject = async (mappingId: string) => {
    setBusy(true); setError('');
    try {
      const updated = await api.post<ItemMapping>(`/item-mappings/${mappingId}/reject`, {});
      setMappings(mappings.map(m => m.id === mappingId ? updated : m));
    } catch (e: any) { setError(e?.message || '拒绝失败'); }
    finally { setBusy(false); }
  };

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  return (
    <main className="p-8 max-w-7xl mx-auto">
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader title="标准项目映射" subtitle="逐项检查并建立合同项目与标准项目的映射" />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: contract items list */}
        <Card>
          <CardHeader title="合同项目" actions={<span className="text-xs text-slate-400">{contractItems.length} 项</span>} />
          <div className="max-h-96 overflow-y-auto">
            {contractItems.length === 0 ? <EmptyState message="暂无合同项目" /> : (
              <ul className="divide-y divide-slate-100">
                {contractItems.map(ci => {
                  const mp = mappingByItem.get(ci.id);
                  return (
                    <li key={ci.id}>
                      <button
                        onClick={() => setSelectedItem(ci)}
                        className={`w-full text-left px-3 py-2.5 text-sm hover:bg-slate-50 ${selectedItem?.id === ci.id ? 'bg-orange-50' : ''}`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs text-slate-500">{ci.line_no}</span>
                          {mp && <StatusBadge status={mp.status} />}
                        </div>
                        <p className="text-slate-700 truncate">{ci.source_description}</p>
                        <p className="text-xs text-slate-400">{ci.unit} · 数量{ci.contract_quantity} · 单价{ci.unit_price}</p>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Card>

        {/* Middle: selected item details + current mapping */}
        <Card>
          <CardHeader title="项目详情" />
          <div className="card-body">
            {!selectedItem ? (
              <EmptyState message="请从左侧选择一个合同项目" />
            ) : (
              <div className="space-y-3 text-sm">
                <div><span className="text-slate-500">项次:</span> <span className="font-mono">{selectedItem.line_no}</span></div>
                <div><span className="text-slate-500">描述:</span> {selectedItem.source_description}</div>
                <div><span className="text-slate-500">单位:</span> {selectedItem.unit || '—'}</div>
                <div><span className="text-slate-500">合同数量:</span> {selectedItem.contract_quantity}</div>
                <div><span className="text-slate-500">合同单价:</span> {selectedItem.unit_price}</div>
                <div><span className="text-slate-500">计算方式:</span> {selectedItem.calculation_method}</div>
                <div><span className="text-slate-500">保留款:</span> {selectedItem.retention_applicable ? '是' : '否'}</div>
                {(() => {
                  const mp = mappingByItem.get(selectedItem.id);
                  if (!mp) return <div className="text-orange-600 text-xs mt-2">尚未映射 — 请从右侧选择标准项目</div>;
                  const si = standardMap.get(mp.standard_item_id);
                  return (
                    <div className="mt-3 p-3 bg-slate-50 rounded text-xs space-y-1">
                      <div><span className="text-slate-500">当前映射:</span> {si?.name || '—'}</div>
                      <div><span className="text-slate-500">状态:</span> <StatusBadge status={mp.status} /></div>
                      <div><span className="text-slate-500">置信度:</span> {formatNumber(mp.confidence * 100)}%</div>
                      {mp.status === 'PENDING_REVIEW' && (
                        <div className="flex gap-2 mt-2">
                          <button onClick={() => handleApprove(mp.id)} disabled={busy} className="btn-primary text-xs px-2 py-1">批准</button>
                          <button onClick={() => handleReject(mp.id)} disabled={busy} className="btn-secondary text-xs px-2 py-1">拒绝</button>
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        </Card>

        {/* Right: standard items search + create mapping */}
        <Card>
          <CardHeader title="标准项目库" />
          <div className="card-body">
            <input
              type="text" placeholder="搜索标准项目..." value={search}
              onChange={e => setSearch(e.target.value)}
              className="input-field text-sm w-full mb-3"
            />
            {!selectedItem ? (
              <EmptyState message="请先选择合同项目" />
            ) : (
              <div className="max-h-80 overflow-y-auto space-y-1">
                {filteredStandards.map(si => {
                  const unitMatch = selectedItem.unit === si.unit;
                  return (
                    <div key={si.id} className="flex items-center justify-between p-2 rounded hover:bg-slate-50">
                      <div>
                        <p className="text-sm text-slate-700">{si.name}</p>
                        <p className="text-xs text-slate-400">{si.code} · {si.unit} · {si.category}</p>
                        {selectedItem.unit && si.unit && (
                          <span className={`text-xs ${unitMatch ? 'text-green-600' : 'text-orange-600'}`}>
                            {unitMatch ? '单位兼容' : '单位不同'}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => handleCreateMapping(si.id)}
                        disabled={busy}
                        className="btn-secondary text-xs px-2 py-1"
                      >
                        建立映射
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </Card>
      </div>
    </main>
  );
}
