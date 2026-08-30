'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Project, Contract, ContractVersion, Application } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState, formatMoney } from '@/components/ui/common';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

type Tab = 'overview' | 'contracts' | 'applications' | 'files' | 'variations' | 'retention' | 'deductions' | 'invoices' | 'collections' | 'budget' | 'audit';

const TAB_LABELS: Record<Tab, string> = {
  overview: '概况',
  contracts: '合同',
  applications: '请款',
  files: '文件',
  variations: '变更',
  retention: '保留款',
  deductions: '扣款',
  invoices: '发票收款',
  collections: '收款单',
  budget: 'Master Budget',
  audit: '审计记录',
};

const LEDGER_TABS: Tab[] = ['variations', 'retention', 'deductions', 'invoices', 'collections', 'budget', 'files', 'audit'];

export default function ProjectDetailPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [project, setProject] = useState<Project | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [tab, setTab] = useState<Tab>('overview');

  // Pending contract versions awaiting approval (DRAFT / UNDER_REVIEW with no approved sibling)
  const [pendingVersions, setPendingVersions] = useState<ContractVersion[]>([]);
  const [pendingContractMap, setPendingContractMap] = useState<Record<string, Contract>>({});
  const [pendingError, setPendingError] = useState('');
  const [approveTarget, setApproveTarget] = useState<{ contractId: string; versionId: string; label: string } | null>(null);
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.get<Project>(`/projects/${projectId}`).then(setProject);
    api.get<Contract[]>(`/contracts?project_id=${projectId}`).then(setContracts);
    api.get<Application[]>(`/payment-applications?project_id=${projectId}`).then(setApplications);
  }, [user, projectId]);

  // When contracts load (or tab switches to contracts), scan each contract for pending versions.
  useEffect(() => {
    if (!user || contracts.length === 0) {
      setPendingVersions([]); setPendingContractMap({}); return;
    }
    let cancelled = false;
    (async () => {
      try {
        const collected: ContractVersion[] = [];
        const map: Record<string, Contract> = {};
        const results = await Promise.all(
          contracts.map(async (c) => {
            try {
              const versions = await api.get<ContractVersion[]>(`/contracts/${c.id}/versions`);
              // A contract has an approved version if any version is APPROVED, or contract.active_version_id is set.
              const hasApproved = !!c.active_version_id || versions.some(v => v.status === 'APPROVED');
              const pending = versions.filter(v => v.status === 'DRAFT' || v.status === 'UNDER_REVIEW');
              return { contract: c, versions: hasApproved ? [] : pending };
            } catch { return { contract: c, versions: [] }; }
          })
        );
        for (const { contract, versions } of results) {
          for (const v of versions) {
            collected.push(v);
            map[v.id] = contract;
          }
        }
        if (!cancelled) {
          setPendingVersions(collected);
          setPendingContractMap(map);
          setPendingError('');
        }
      } catch (e: any) {
        if (!cancelled) setPendingError(e?.message || '加载待审版本失败');
      }
    })();
    return () => { cancelled = true; };
  }, [user, contracts]);

  const handleApprove = async () => {
    if (!approveTarget) return;
    setApproving(true);
    try {
      await api.post(`/contracts/${approveTarget.contractId}/versions/${approveTarget.versionId}/approve`);
      // Refresh contracts so pending list re-evaluates
      const refreshed = await api.get<Contract[]>(`/contracts?project_id=${projectId}`);
      setContracts(refreshed);
      setApproveTarget(null);
    } catch (e: any) {
      setPendingError(e?.message || '批准失败');
    } finally {
      setApproving(false);
    }
  };

  if (loading || !project) return <div className="p-8">加载中...</div>;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <PageHeader title={project.project_name} subtitle={`${project.internal_project_code} · ${project.currency}`} />

      <div className="flex gap-1 border-b border-slate-200 mb-6 overflow-x-auto">
        {(Object.keys(TAB_LABELS) as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm whitespace-nowrap ${tab === t ? 'tab-active' : 'tab-inactive'}`}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <Card>
          <CardHeader title="项目概况" />
          <div className="card-body">
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-xs text-slate-500 mb-1">状态</dt>
                <dd><StatusBadge status={project.status} /></dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500 mb-1">币别</dt>
                <dd className="text-sm text-slate-800">{project.currency}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500 mb-1">默认税率</dt>
                <dd className="text-sm text-slate-800">{project.default_tax_rate}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500 mb-1">说明</dt>
                <dd className="text-sm text-slate-800">{project.description || '—'}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-xs text-slate-500 mb-1">特有款说明</dt>
                <dd className="text-sm text-slate-800">{(project as any).special_fund_description || '无'}</dd>
              </div>
            </dl>
          </div>
        </Card>
      )}

      {tab === 'contracts' && (
        <>
          {pendingVersions.length > 0 && (
            <Card className="mb-4 border-orange-200">
              <div className="card-body">
                <p className="text-orange-700 font-semibold mb-2">待批准合同版本 <span className="ml-1 text-xs font-normal text-slate-500">（项目尚无 APPROVED 版本，Master Budget 等功能不可用）</span></p>
                {pendingError && <ErrorBanner message={pendingError} onDismiss={() => setPendingError('')} />}
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>合同编号</th>
                      <th>版本</th>
                      <th>状态</th>
                      <th className="text-right">含税金额</th>
                      <th>变更原因</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingVersions.map(v => {
                      const c = pendingContractMap[v.id];
                      const label = `${c?.external_contract_no || '—'} v${v.version_no}`;
                      const canApprove = v.status === 'UNDER_REVIEW' || v.status === 'DRAFT';
                      return (
                        <tr key={v.id} className="bg-orange-50/40">
                          <td>{c?.external_contract_no || '—'}</td>
                          <td>v{v.version_no}</td>
                          <td><StatusBadge status={v.status} /></td>
                          <td className="num">{formatMoney(v.amount_inc_tax)}</td>
                          <td className="text-xs text-slate-600">{v.change_reason || '—'}</td>
                          <td>
                            {canApprove ? (
                              <button
                                onClick={() => setApproveTarget({ contractId: v.contract_id, versionId: v.id, label })}
                                disabled={approving}
                                className="btn-primary text-xs"
                              >
                                批准此版本
                              </button>
                            ) : (
                              <span className="text-xs text-slate-400">不可批准</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
          <Card>
            <CardHeader title="合同" />
            <div className="card-body">
              {contracts.length === 0 ? (
                <EmptyState message="暂无合同" />
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>合同编号</th>
                      <th>名称</th>
                      <th>税务模式</th>
                      <th>税率</th>
                      <th>状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contracts.map(c => (
                      <tr key={c.id}>
                        <td>{c.external_contract_no}</td>
                        <td>{c.contract_name}</td>
                        <td>{c.tax_mode}</td>
                        <td>{c.tax_rate}</td>
                        <td><StatusBadge status={c.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </Card>
        </>
      )}

      {approveTarget && (
        <ConfirmDialog
          title="批准合同版本"
          message={`确认批准 ${approveTarget.label}？批准后该版本成为合同当前生效版本，Master Budget 等功能即可显示数据。`}
          confirmLabel={approving ? '批准中...' : '确认批准'}
          onConfirm={handleApprove}
          onCancel={() => { if (!approving) setApproveTarget(null); }}
        />
      )}

      {tab === 'applications' && (
        <Card>
          <CardHeader
            title="请款"
            actions={
              <Link href="/applications/new" className="btn-primary">新建请款</Link>
            }
          />
          <div className="card-body">
            <table className="data-table">
              <thead>
                <tr>
                  <th>请款编号</th>
                  <th>期数</th>
                  <th>状态</th>
                  <th className="text-right">本期完成</th>
                  <th className="text-right">保留款</th>
                  <th className="text-right">含税金额</th>
                </tr>
              </thead>
              <tbody>
                {applications.map(a => (
                  <tr key={a.id}>
                    <td>
                      <Link href={`/applications/${a.id}`} className="text-orange-600 hover:underline">
                        {a.application_no}
                      </Link>
                    </td>
                    <td>第{a.period_no}期</td>
                    <td><StatusBadge status={a.status} /></td>
                    <td className="num">{formatMoney(a.gross_completed_amount)}</td>
                    <td className="num">{formatMoney(a.retention_held_amount)}</td>
                    <td className="num">{formatMoney(a.invoice_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'files' && (
        <Card>
          <div className="card-body">
            <Link href={`/projects/${projectId}/files`} className="btn-secondary inline-flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
              查看文件档案 →
            </Link>
          </div>
        </Card>
      )}

      {LEDGER_TABS.includes(tab) && (
        <Card>
          <div className="card-body">
            <Link
              href={`/projects/${projectId}/${tab}`}
              className="btn-secondary inline-flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
              查看{TAB_LABELS[tab]}台账 →
            </Link>
          </div>
        </Card>
      )}
    </main>
  );
}
