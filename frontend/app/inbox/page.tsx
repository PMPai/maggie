'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState, useRef, useCallback } from 'react';
import { api } from '@/lib/api';
import type { FileInboxItem, Project } from '@/lib/types';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge } from '@/components/ui/common';
import { FilterBar } from '@/components/ui/FilterBar';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { DocumentPreview } from '@/components/ui/DocumentPreview';

export default function InboxPage() {
  const { user, loading } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [items, setItems] = useState<FileInboxItem[]>([]);
  const [error, setError] = useState('');
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollDelayRef = useRef(3000);

  useEffect(() => {
    if (!user) return;
    api.get<Project[]>('/projects').then(setProjects).catch(() => {});
  }, [user]);

  const loadItemsRef = useRef<() => Promise<void>>(() => Promise.resolve());

  const loadItems = useCallback(async () => {
    if (!selectedProject) return;
    try {
      const data = await api.get<FileInboxItem[]>(`/documents?project_id=${selectedProject}`);
      setItems(data);
      if (pollRef.current) {
        clearTimeout(pollRef.current);
        pollRef.current = null;
      }
      const hasPending = data.some(d => d.ocr_status === 'PENDING' || d.ocr_status === 'RUNNING');
      if (!hasPending) {
        pollDelayRef.current = 3000;
        return;
      }
      pollDelayRef.current = Math.min(pollDelayRef.current * 1.5, 15000);
      pollRef.current = setTimeout(() => { void loadItemsRef.current(); }, pollDelayRef.current);
    } catch (e) {
      const msg = e instanceof Error ? e.message : '加载失败';
      setError(msg);
    }
  }, [selectedProject]);

  useEffect(() => {
    loadItemsRef.current = loadItems;
  }, [loadItems]);

  useEffect(() => {
    if (selectedProject) {
      pollDelayRef.current = 3000;
      loadItems();
    } else {
      setItems([]);
    }
    return () => {
      if (pollRef.current) {
        clearTimeout(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [loadItems, selectedProject]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    if (!selectedProject) {
      setError('请先选择项目');
      return;
    }
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append('file', file);
        await api.upload(`/documents/upload?project_id=${selectedProject}&document_type=CONTRACT`, formData);
      }
      if (fileInputRef.current) fileInputRef.current.value = '';
      pollDelayRef.current = 3000;
      await loadItems();
    } catch (e) {
      const msg = e instanceof Error ? e.message : '上传失败';
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  if (loading) return <PageLoader />;

  return (
    <>
      <PageHeader title="文件收件箱" subtitle="上传、OCR 识别、预览与下载" />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <FilterBar
        filters={[{
          label: '项目',
          value: selectedProject,
          options: projects.map(p => ({ label: p.internal_project_code, value: p.id })),
          onChange: (v) => setSelectedProject(v),
        }]}
      />
      <Card className="mb-4">
        <CardHeader title="上传文件" />
        <div className="card-body flex items-center">
          <input ref={fileInputRef} type="file" multiple onChange={e => handleUpload(e.target.files)} className="hidden" />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || !selectedProject}
            className="btn-primary disabled:opacity-50"
          >
            {uploading ? '上传中...' : '选择文件上传'}
          </button>
          <span className="ml-3 text-xs text-slate-400">
            {selectedProject ? '支持 PDF / 图片 / Excel / CSV / 邮件' : '请先选择项目后再上传'}
          </span>
        </div>
      </Card>
      <Card>
        <CardHeader
          title="文件列表"
          actions={
            <button
              onClick={loadItems}
              disabled={!selectedProject}
              className="btn-secondary text-sm px-3 py-1 disabled:opacity-50"
            >
              刷新
            </button>
          }
        />
        <div className="overflow-x-auto scrollbar-thin">
          {items.length === 0 ? (
            <EmptyState message={selectedProject ? '暂无文件' : '请先选择项目'} />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>原文件名</th>
                  <th>类型</th>
                  <th>大小</th>
                  <th>SHA-256</th>
                  <th>OCR 状态</th>
                  <th>上传时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map(it => (
                  <tr key={it.id}>
                    <td className="text-sm">{it.original_name}</td>
                    <td>{it.document_type}</td>
                    <td className="num">{(it.size_bytes / 1024).toFixed(1)} KB</td>
                    <td className="font-mono text-xs">{it.sha256.substring(0, 8)}…</td>
                    <td><StatusBadge status={it.ocr_status} /></td>
                    <td className="text-sm text-slate-500">{it.uploaded_at ? it.uploaded_at.substring(0, 16).replace('T', ' ') : '—'}</td>
                    <td className="whitespace-nowrap">
                      <button onClick={() => setPreviewId(it.id)} className="text-blue-600 text-sm hover:underline mr-2">预览</button>
                      <a href={`/api/documents/${it.id}/download`} className="text-orange-600 text-sm hover:underline">下载</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>

      {previewId && (
        <div
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
          onClick={() => setPreviewId(null)}
        >
          <div
            className="bg-white rounded-lg p-4 max-w-4xl w-full max-h-[90vh] overflow-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-semibold">文件预览</h3>
              <button onClick={() => setPreviewId(null)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>
            <DocumentPreview documentId={previewId} />
          </div>
        </div>
      )}
    </>
  );
}
