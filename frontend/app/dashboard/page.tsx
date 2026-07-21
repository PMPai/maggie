'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Project } from '@/lib/types';
import Link from 'next/link';

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    if (user) api.get<Project[]>('/projects').then(setProjects).catch(() => {});
  }, [user]);

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">管理驾驶舱</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="text-sm text-gray-500">项目数</h2>
          <p className="text-3xl font-bold">{projects.length}</p>
        </div>
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="text-sm text-gray-500">用户</h2>
          <p className="text-lg">{user.display_name}</p>
          <p className="text-sm text-gray-500">{user.roles.join(', ')}</p>
        </div>
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="text-sm text-gray-500">待审核请款</h2>
          <p className="text-3xl font-bold">0</p>
        </div>
      </div>
      <h2 className="text-xl font-bold mb-4">项目列表</h2>
      <div className="rounded-lg bg-white shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">项目编号</th>
              <th className="px-4 py-2 text-left">工程名称</th>
              <th className="px-4 py-2 text-left">状态</th>
            </tr>
          </thead>
          <tbody>
            {projects.map(p => (
              <tr key={p.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2"><Link href={`/projects/${p.id}`} className="text-blue-600 hover:underline">{p.internal_project_code}</Link></td>
                <td className="px-4 py-2">{p.project_name}</td>
                <td className="px-4 py-2">{p.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
