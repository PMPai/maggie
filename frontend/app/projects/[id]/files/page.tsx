'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useParams } from 'next/navigation';
import type { FileInboxItem } from '@/lib/types';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { DocumentPreview } from '@/components/ui/DocumentPreview';

export default function FileArchivePage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [docs, setDocs] = useState<FileInboxItem[]>([]);
  const [previewId, setPreviewId] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api.get<FileInboxItem[]>(`/documents?project_id=${projectId}`).then(setDocs).catch(() => {});
  }, [user, projectId]);

  if (loading) return <PageLoader />;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <PageHeader title="文件档案" subtitle="按项目浏览、预览与下载" />
      <Card>
        <CardHeader title={`文件列表 (${docs.length})`} />
        <div className="overflow-x-auto">
          {docs.length === 0 ? <EmptyState message="暂无文件" /> : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>原文件名</th><th>类型</th><th>大小</th><th>SHA-256</th>
                  <th>OCR 状态</th><th>上传时间</th><th>操作</th>
                </tr>
              </thead>
              <tbody>
                {docs.map(d => (
                  <tr key={d.id}>
                    <td className="text-sm">{d.original_name}</td>
                    <td>{d.document_type}</td>
                    <td className="num">{(d.size_bytes / 1024).toFixed(1)} KB</td>
                    <td className="font-mono text-xs">{d.sha256.substring(0, 8)}…</td>
                    <td><StatusBadge status={d.ocr_status} /></td>
                    <td className="text-sm text-slate-500">{d.uploaded_at?.substring(0, 16).replace('T', ' ')}</td>
                    <td>
                      <button onClick={() => setPreviewId(d.id)} className="text-blue-600 text-sm hover:underline mr-2">预览</button>
                      <a href={`/api/documents/${d.id}/download`} className="text-orange-600 text-sm hover:underline">下载</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
      {previewId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setPreviewId(null)}>
          <div className="bg-white rounded-lg p-4 max-w-4xl w-full max-h-[90vh] overflow-auto" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between mb-2"><h3 className="font-semibold">文件预览</h3><button onClick={() => setPreviewId(null)}>✕</button></div>
            <DocumentPreview documentId={previewId} />
          </div>
        </div>
      )}
    </main>
  );
}
