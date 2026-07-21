'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Project, Contract, Application } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function ProjectDetailPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [project, setProject] = useState<Project | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [tab, setTab] = useState<'overview' | 'contracts' | 'applications' | 'files'>('overview');

  useEffect(() => {
    if (!user) return;
    api.get<Project>(`/projects/${projectId}`).then(setProject);
    api.get<Contract[]>(`/contracts?project_id=${projectId}`).then(setContracts);
    api.get<Application[]>(`/payment-applications?project_id=${projectId}`).then(setApplications);
  }, [user, projectId]);

  if (loading || !project) return <div className="p-8">加载中...</div>;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">{project.project_name}</h1>
      <p className="text-gray-500 mb-6">{project.internal_project_code} · {project.currency}</p>
      <div className="flex gap-4 border-b mb-6">
        {(['overview', 'contracts', 'applications', 'files'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-2 ${tab === t ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'}`}>
            {{overview:'项目概况',contracts:'合同',applications:'请款',files:'文件'}[t]}
          </button>
        ))}
      </div>
      {tab === 'overview' && (
        <div className="space-y-2">
          <p><strong>状态：</strong>{project.status}</p>
          <p><strong>币别：</strong>{project.currency}</p>
          <p><strong>默认税率：</strong>{project.default_tax_rate}</p>
          <p><strong>说明：</strong>{project.description || '—'}</p>
        </div>
      )}
      {tab === 'contracts' && (
        <div>
          <Link href={`/projects/${projectId}/contracts`} className="text-blue-600 hover:underline">查看合同版本及项目 →</Link>
          <table className="w-full mt-4">
            <thead className="bg-gray-50"><tr><th className="px-4 py-2 text-left">合同编号</th><th className="px-4 py-2 text-left">名称</th><th className="px-4 py-2 text-left">状态</th></tr></thead>
            <tbody>
              {contracts.map(c => (
                <tr key={c.id} className="border-t"><td className="px-4 py-2">{c.external_contract_no}</td><td className="px-4 py-2">{c.contract_name}</td><td className="px-4 py-2">{c.status}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {tab === 'applications' && (
        <div>
          <Link href="/applications/new" className="text-blue-600 hover:underline">新建请款 →</Link>
          <table className="w-full mt-4">
            <thead className="bg-gray-50"><tr><th className="px-4 py-2 text-left">请款编号</th><th className="px-4 py-2 text-left">期数</th><th className="px-4 py-2 text-left">状态</th><th className="px-4 py-2 text-right">含税金额</th></tr></thead>
            <tbody>
              {applications.map(a => (
                <tr key={a.id} className="border-t"><td className="px-4 py-2">{a.application_no}</td><td className="px-4 py-2">第{a.period_no}期</td><td className="px-4 py-2">{a.status}</td><td className="px-4 py-2 text-right">{Number(a.invoice_amount).toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {tab === 'files' && <p className="text-gray-500">文件档案将在后续阶段完善</p>}
    </main>
  );
}
