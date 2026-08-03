'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Project, Contract, Application } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState, formatMoney } from '@/components/ui/common';

type Tab = 'overview' | 'contracts' | 'applications' | 'files' | 'variations' | 'retention' | 'deductions' | 'invoices' | 'catalog' | 'mapping' | 'budget' | 'audit';

const TAB_LABELS: Record<Tab, string> = {
  overview: '概况',
  contracts: '合同',
  applications: '请款',
  files: '文件',
  variations: '变更',
  retention: '保留款',
  deductions: '扣款',
  invoices: '发票收款',
  catalog: '标准项目',
  mapping: '映射',
  budget: 'Master Budget',
  audit: '审计记录',
};

const LEDGER_TABS: Tab[] = ['variations', 'retention', 'deductions', 'invoices', 'catalog', 'mapping', 'budget', 'files', 'audit'];

export default function ProjectDetailPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [project, setProject] = useState<Project | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [tab, setTab] = useState<Tab>('overview');

  useEffect(() => {
    if (!user) return;
    api.get<Project>(`/projects/${projectId}`).then(setProject);
    api.get<Contract[]>(`/contracts?project_id=${projectId}`).then(setContracts);
    api.get<Application[]>(`/payment-applications?project_id=${projectId}`).then(setApplications);
  }, [user, projectId]);

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
            </dl>
          </div>
        </Card>
      )}

      {tab === 'contracts' && (
        <Card>
          <CardHeader title="合同" />
          <div className="card-body">
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
          </div>
        </Card>
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
