'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { StandardItem } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function CatalogPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [items, setItems] = useState<StandardItem[]>([]);

  useEffect(() => {
    if (!user) return;
    api.get<StandardItem[]>('/standard-items').then(setItems).catch(() => setItems([]));
  }, [user]);

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-blue-600 hover:underline">← 返回项目</Link>
      </div>
      <h1 className="text-2xl font-bold mb-6">标准项字典</h1>

      <div className="rounded-lg bg-white shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">编号</th>
              <th className="px-4 py-2 text-left">名称</th>
              <th className="px-4 py-2 text-left">类别</th>
              <th className="px-4 py-2 text-left">单位</th>
              <th className="px-4 py-2 text-left">状态</th>
            </tr>
          </thead>
          <tbody>
            {items.map(i => (
              <tr key={i.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2 font-mono">{i.code}</td>
                <td className="px-4 py-2">{i.name}</td>
                <td className="px-4 py-2">{i.category}</td>
                <td className="px-4 py-2">{i.unit}</td>
                <td className="px-4 py-2">{i.is_active ? <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">启用</span> : <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">停用</span>}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={5} className="px-4 py-4 text-center text-gray-500">暂无标准项</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
