'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { StandardItem } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, EmptyState } from '@/components/ui/common';

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
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader title="标准项目目录" />

      <Card>
        <CardHeader title="标准项目" />
        <div className="card-body">
          {items.length === 0 ? (
            <EmptyState message="暂无标准项" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>编号</th>
                  <th>名称</th>
                  <th>类别</th>
                  <th>单位</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {items.map(i => (
                  <tr key={i.id}>
                    <td className="font-mono">{i.code}</td>
                    <td>{i.name}</td>
                    <td>{i.category}</td>
                    <td>{i.unit}</td>
                    <td>
                      {i.is_active ? (
                        <span className="badge badge-green">启用</span>
                      ) : (
                        <span className="badge badge-gray">停用</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </main>
  );
}
