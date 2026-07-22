'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Project } from '@/lib/types';
import Link from 'next/link';
import { PageHeader, StatCard, Card, CardHeader, StatusBadge, EmptyState } from '@/components/ui/common';

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    if (user) api.get<Project[]>('/projects').then(setProjects).catch(() => {});
  }, [user]);

  if (loading) return <div className="p-8 text-slate-500">加载中...</div>;
  if (!user) return <div className="p-8 text-slate-500">请先登录</div>;

  return (
    <div>
      <PageHeader
        title="管理驾驶舱"
        subtitle={`当前用户：${user.display_name}（${user.roles.join(', ')}）`}
      />

      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard
          label="项目数"
          value={projects.length}
          icon="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
          color="blue"
        />
        <StatCard
          label="当前用户"
          value={user.display_name}
          icon="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
          color="slate"
        />
        <StatCard
          label="待审核请款"
          value={0}
          icon="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          color="orange"
        />
      </div>

      <Card>
        <CardHeader title="项目列表" />
        <div className="overflow-x-auto">
          {projects.length === 0 ? (
            <EmptyState message="暂无项目数据" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>项目编号</th>
                  <th>工程名称</th>
                  <th>状态</th>
                  <th>币别</th>
                  <th>税率</th>
                </tr>
              </thead>
              <tbody>
                {projects.map(p => (
                  <tr key={p.id}>
                    <td>
                      <Link href={`/projects/${p.id}`} className="text-blue-600 hover:underline">
                        {p.internal_project_code}
                      </Link>
                    </td>
                    <td>{p.project_name}</td>
                    <td><StatusBadge status={p.status} /></td>
                    <td>{p.currency}</td>
                    <td>{p.default_tax_rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
