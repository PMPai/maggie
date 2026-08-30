'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, EmptyState, formatMoney } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

interface Collection {
  id: string;
  receipt_no: string;
  receipt_date: string | null;
  amount_received: number | string;
  status: string;
}

export default function CollectionsPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [collections, setCollections] = useState<Collection[]>([]);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    contract_id: '',
    receipt_no: '',
    amount_received: '',
    receipt_date: '',
  });

  const fetchCollections = async () => {
    try {
      const res = await api.get<Collection[]>(`/collections?project_id=${projectId}`);
      setCollections(res);
    } catch (e: any) {
      setError(e?.message || '加载失败');
    } finally {
      setLoaded(true);
    }
  };

  useEffect(() => {
    if (!user) return;
    fetchCollections();
  }, [user, projectId]);

  if (loading) return <PageLoader />;

  const handleCreate = async () => {
    if (!createForm.contract_id || !createForm.receipt_no || !createForm.amount_received) {
      setError('合同、收款单号、金额为必填');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await api.post('/collections', {
        project_id: projectId,
        contract_id: createForm.contract_id,
        receipt_no: createForm.receipt_no,
        amount_received: createForm.amount_received,
        receipt_date: createForm.receipt_date || null,
        status: 'PLANNED',
      });
      setShowCreate(false);
      setCreateForm({ contract_id: '', receipt_no: '', amount_received: '', receipt_date: '' });
      await fetchCollections();
    } catch (e: any) {
      setError(e?.message || '创建失败');
    } finally {
      setBusy(false);
    }
  };

  const handleAction = async (id: string, action: 'confirm' | 'receive') => {
    setBusy(true);
    setError('');
    try {
      await api.patch(`/collections/${id}/${action}`);
      await fetchCollections();
    } catch (e: any) {
      setError(e?.message || '操作失败');
    } finally {
      setBusy(false);
    }
  };

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      PLANNED: 'badge-blue',
      CONFIRMED: 'badge-amber',
      RECEIVED: 'badge-green',
      CANCELLED: 'badge-gray',
    };
    const label: Record<string, string> = {
      PLANNED: '已排程',
      CONFIRMED: '已确认',
      RECEIVED: '已收款',
      CANCELLED: '已取消',
    };
    return <span className={`badge ${map[status] || 'badge-gray'}`}>{label[status] || status}</span>;
  };

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <PageHeader
        title="收款单管理"
        subtitle="收款单状态流：已排程 → 已确认 → 已收款"
        actions={
          <button onClick={() => setShowCreate(!showCreate)} className="btn-primary text-sm">
            {showCreate ? '取消' : '+ 新建收款单'}
          </button>
        }
      />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      {showCreate && (
        <Card className="mb-4">
          <CardHeader title="新建收款单" />
          <div className="card-body grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">合同 ID *</label>
              <input type="text" value={createForm.contract_id}
                onChange={e => setCreateForm({...createForm, contract_id: e.target.value})}
                className="input-field text-sm" placeholder="合同 UUID" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">收款单号 *</label>
              <input type="text" value={createForm.receipt_no}
                onChange={e => setCreateForm({...createForm, receipt_no: e.target.value})}
                className="input-field text-sm" placeholder="例如 RCV-001" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">金额 *</label>
              <input type="number" value={createForm.amount_received}
                onChange={e => setCreateForm({...createForm, amount_received: e.target.value})}
                className="input-field text-sm" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">预定收款日</label>
              <input type="date" value={createForm.receipt_date}
                onChange={e => setCreateForm({...createForm, receipt_date: e.target.value})}
                className="input-field text-sm" />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button onClick={handleCreate} disabled={busy} className="btn-primary text-sm">
              {busy ? '创建中...' : '创建'}
            </button>
          </div>
        </Card>
      )}

      {loaded && collections.length === 0 && !error && (
        <EmptyState message="暂无收款单记录" />
      )}

      {collections.length > 0 && (
        <Card>
          <div className="overflow-x-auto">
            <table className="data-table text-xs">
              <thead>
                <tr>
                  <th>收款单号</th><th>预定日期</th>
                  <th className="text-right">金额</th><th>状态</th><th>操作</th>
                </tr>
              </thead>
              <tbody>
                {collections.map(c => (
                  <tr key={c.id}>
                    <td className="font-mono">{c.receipt_no}</td>
                    <td>{c.receipt_date || '—'}</td>
                    <td className="num">{formatMoney(parseFloat(String(c.amount_received)) || 0)}</td>
                    <td>{statusBadge(c.status)}</td>
                    <td>
                      {c.status === 'PLANNED' && (
                        <button onClick={() => handleAction(c.id, 'confirm')} disabled={busy}
                          className="text-xs text-orange-600 hover:underline">确认</button>
                      )}
                      {c.status === 'CONFIRMED' && (
                        <button onClick={() => handleAction(c.id, 'receive')} disabled={busy}
                          className="text-xs text-green-600 hover:underline">标记收款</button>
                      )}
                      {(c.status === 'RECEIVED' || c.status === 'CANCELLED') && (
                        <span className="text-slate-300 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </main>
  );
}
