'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import type { Contract, ContractVersion, ContractItem, FileInboxItem } from '@/lib/types';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge, formatMoney } from '@/components/ui/common';
import { DocumentPreview } from '@/components/ui/DocumentPreview';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

type Action = 'save' | 'submit' | 'approve';

function blankItem(versionId: string, sortOrder: number): ContractItem {
  return {
    id: '', contract_version_id: versionId, parent_item_id: null,
    line_no: String(sortOrder + 1), item_code: null, source_description: '',
    unit: '', contract_quantity: '0', unit_price: '0', line_amount: '0',
    calculation_method: 'QUANTITY', is_heading: false, is_billable: true,
    retention_applicable: true, sort_order: sortOrder,
  };
}

export default function ExtractPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const router = useRouter();
  const contractId = params.id as string;

  const [contract, setContract] = useState<Contract | null>(null);
  const [version, setVersion] = useState<ContractVersion | null>(null);
  const [items, setItems] = useState<ContractItem[]>([]);
  const [doc, setDoc] = useState<FileInboxItem | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [confirm, setConfirm] = useState<null | Action>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [editedItemIds, setEditedItemIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (loading || !user) return;
    api.get<Contract>(`/contracts/${contractId}`).then(setContract)
      .catch(e => setError(e instanceof Error ? e.message : '加载合同失败'));
    api.get<ContractVersion[]>(`/contracts/${contractId}/versions`).then(versions => {
      const v = versions.find(x => x.status === 'DRAFT' || x.status === 'UNDER_REVIEW') || versions[versions.length - 1] || null;
      if (!v) { setError('该合同暂无版本'); return; }
      setVersion(v);
      setForm({
        amount_ex_tax: v.amount_ex_tax,
        tax_amount: v.tax_amount,
        amount_inc_tax: v.amount_inc_tax,
        change_reason: v.change_reason || '',
      });
      api.get<ContractItem[]>(`/contracts/contract-versions/${v.id}/items`).then(setItems).catch(() => {});
      if (v.source_document_id) {
        api.get<FileInboxItem>(`/documents/${v.source_document_id}`).then(setDoc).catch(() => {});
      }
    }).catch(e => setError(e instanceof Error ? e.message : '加载版本失败'));
  }, [user, loading, contractId]);

  const validate = (): string[] => {
    const errs: string[] = [];
    const ex = parseFloat(form.amount_ex_tax || '0');
    const tax = parseFloat(form.tax_amount || '0');
    const inc = parseFloat(form.amount_inc_tax || '0');
    if (Math.abs(ex + tax - inc) > 0.01) errs.push('未税金额 + 税额 ≠ 含税金额');
    const itemsTotal = items.reduce((s, it) => s + parseFloat(it.line_amount || '0'), 0);
    if (Math.abs(itemsTotal - ex) > 0.01)
      errs.push(`项目行合计 (${formatMoney(itemsTotal)}) ≠ 未税金额 (${formatMoney(ex)})`);
    return errs;
  };

  const patchItem = (index: number, patch: Partial<ContractItem>) => {
    const target = items[index];
    if (target && target.id !== '') {
      setEditedItemIds(prev => prev.has(target.id) ? prev : new Set(prev).add(target.id));
    }
    setItems(prev => prev.map((it, i) => i === index ? { ...it, ...patch } : it));
  };

  const recalc = (index: number, qty?: string, price?: string) => {
    const it = items[index];
    const q = parseFloat(qty ?? it.contract_quantity) || 0;
    const p = parseFloat(price ?? it.unit_price) || 0;
    patchItem(index, {
      ...(qty !== undefined ? { contract_quantity: qty } : {}),
      ...(price !== undefined ? { unit_price: price } : {}),
      line_amount: String(q * p),
    });
  };

  const saveNewItems = async (versionId: string): Promise<ContractItem[]> => {
    const updated = [...items];
    for (let i = 0; i < updated.length; i++) {
      if (updated[i].id === '' && updated[i].source_description.trim()) {
        const created = await api.post<ContractItem>(`/contracts/contract-versions/${versionId}/items`, {
          line_no: updated[i].line_no,
          source_description: updated[i].source_description,
          unit: updated[i].unit || null,
          contract_quantity: updated[i].contract_quantity,
          unit_price: updated[i].unit_price,
          line_amount: updated[i].line_amount,
          calculation_method: updated[i].calculation_method,
          is_heading: updated[i].is_heading,
          is_billable: updated[i].is_billable,
          retention_applicable: updated[i].retention_applicable,
          sort_order: updated[i].sort_order,
        });
        updated[i] = created;
      } else if (updated[i].id !== '' && editedItemIds.has(updated[i].id)) {
        const patched = await api.patch<ContractItem>(
          `/contracts/contract-versions/${versionId}/items/${updated[i].id}`,
          {
            line_no: updated[i].line_no,
            source_description: updated[i].source_description,
            unit: updated[i].unit || null,
            contract_quantity: updated[i].contract_quantity,
            unit_price: updated[i].unit_price,
            line_amount: updated[i].line_amount,
            calculation_method: updated[i].calculation_method,
            retention_applicable: updated[i].retention_applicable,
          },
        );
        updated[i] = patched;
      }
    }
    return updated;
  };

  const openConfirm = (action: Action) => {
    const errs = validate();
    setValidationErrors(errs);
    if (action === 'save' || errs.length === 0) {
      setConfirm(action);
    }
  };

  const doAction = async (action: Action) => {
    if (!version) return;
    const errs = validate();
    setValidationErrors(errs);
    if (errs.length > 0 && action !== 'save') {
      setConfirm(null);
      return;
    }
    setBusy(true);
    try {
      const patchBody: Record<string, unknown> = {
        amount_ex_tax: form.amount_ex_tax,
        tax_amount: form.tax_amount,
        amount_inc_tax: form.amount_inc_tax,
        change_reason: form.change_reason || null,
      };
      if (action === 'submit' && version.status === 'DRAFT') {
        patchBody.status = 'UNDER_REVIEW';
      }
      const patched = await api.patch<ContractVersion>(`/contracts/contract-versions/${version.id}`, patchBody);
      setVersion(patched);
      const updatedItems = await saveNewItems(version.id);
      setItems(updatedItems);
      setEditedItemIds(new Set());
      if (action === 'approve') {
        await api.post(`/contracts/${contractId}/versions/${version.id}/approve`);
      }
      setConfirm(null);
      if (action === 'approve' && contract) {
        router.push(`/projects/${contract.project_id}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '操作失败');
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  };

  if (loading) return <PageLoader message="加载中..." />;
  if (!user) return <div className="p-8">请先登录</div>;
  if (!contract || !version) {
    return (
      <main className="p-8 max-w-7xl mx-auto">
        {error ? <ErrorBanner message={error} onDismiss={() => setError('')} /> : <PageLoader message="加载合同..." />}
      </main>
    );
  }

  const readOnly = version.status !== 'DRAFT' && version.status !== 'UNDER_REVIEW';
  const sourceDocId = version.source_document_id;
  const itemsTotal = items.reduce((s, it) => s + parseFloat(it.line_amount || '0'), 0);

  return (
    <main className="p-8 max-w-7xl mx-auto">
      <div className="mb-3">
        <Link href={`/projects/${contract.project_id}`} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-orange-600 transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          返回项目
        </Link>
      </div>

      <PageHeader
        title="合同抽取审核"
        subtitle={`${contract.external_contract_no} · ${contract.contract_name} · v${version.version_no}`}
        actions={<StatusBadge status={version.status} />}
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Left panel: Document preview + OCR text */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader title="原始文件" />
            <div className="card-body">
              {sourceDocId ? (
                <DocumentPreview documentId={sourceDocId} className="h-[600px]" />
              ) : (
                <EmptyState message="无关联文档" />
              )}
              {doc?.ocr_text && (
                <details className="mt-3">
                  <summary className="text-sm text-slate-600 cursor-pointer">OCR 原文</summary>
                  <pre className="text-xs bg-slate-50 p-3 mt-2 rounded max-h-60 overflow-auto whitespace-pre-wrap">{doc.ocr_text}</pre>
                </details>
              )}
            </div>
          </Card>
        </div>

        {/* Right panel: Form + Items + Validation + Actions */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader title="合同字段" />
            <div className="card-body">
              <div className="grid grid-cols-2 gap-x-6 gap-y-3 mb-4 text-sm">
                <div>
                  <p className="text-xs text-slate-500">合同编号</p>
                  <p className="font-medium text-slate-800 mt-0.5">{contract.external_contract_no}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">合同名称</p>
                  <p className="font-medium text-slate-800 mt-0.5">{contract.contract_name}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">币种 / 税模式</p>
                  <p className="font-medium text-slate-800 mt-0.5">{contract.currency} / {contract.tax_mode}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">税率</p>
                  <p className="font-medium text-slate-800 mt-0.5">{(parseFloat(contract.tax_rate) * 100).toFixed(2)}%</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-xs text-slate-600">
                  未税金额
                  <input type="number" disabled={readOnly || busy} value={form.amount_ex_tax || ''}
                    onChange={e => setForm({ ...form, amount_ex_tax: e.target.value })}
                    className="input-field text-sm mt-1" />
                </label>
                <label className="text-xs text-slate-600">
                  税额
                  <input type="number" disabled={readOnly || busy} value={form.tax_amount || ''}
                    onChange={e => setForm({ ...form, tax_amount: e.target.value })}
                    className="input-field text-sm mt-1" />
                </label>
                <label className="text-xs text-slate-600">
                  含税金额
                  <input type="number" disabled={readOnly || busy} value={form.amount_inc_tax || ''}
                    onChange={e => setForm({ ...form, amount_inc_tax: e.target.value })}
                    className="input-field text-sm mt-1" />
                </label>
                <label className="text-xs text-slate-600">
                  变更原因
                  <input type="text" disabled={readOnly || busy} value={form.change_reason || ''}
                    onChange={e => setForm({ ...form, change_reason: e.target.value })}
                    className="input-field text-sm mt-1" />
                </label>
              </div>
            </div>
          </Card>

          <Card className="mt-4">
            <CardHeader
              title="合同项目"
              actions={
                !readOnly ? (
                  <button onClick={() => setItems([...items, blankItem(version.id, items.length)])}
                    disabled={busy}
                    className="btn-secondary text-sm">
                    + 添加行
                  </button>
                ) : undefined
              }
            />
            <div className="overflow-x-auto">
              <table className="data-table text-xs">
                <thead>
                  <tr>
                    <th>项次</th>
                    <th>描述</th>
                    <th>单位</th>
                    <th className="text-right">数量</th>
                    <th className="text-right">单价</th>
                    <th className="text-right">金额</th>
                    {!readOnly && <th></th>}
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, i) => (
                    <tr key={it.id || `new-${i}`}>
                      <td>
                        <input value={it.line_no} disabled={readOnly || busy}
                          onChange={e => patchItem(i, { line_no: e.target.value })}
                          className="input-field text-xs w-16" />
                      </td>
                      <td>
                        <input value={it.source_description} disabled={readOnly || busy}
                          onChange={e => patchItem(i, { source_description: e.target.value })}
                          className="input-field text-xs w-full" />
                      </td>
                      <td>
                        <input value={it.unit || ''} disabled={readOnly || busy}
                          onChange={e => patchItem(i, { unit: e.target.value })}
                          className="input-field text-xs w-16" />
                      </td>
                      <td>
                        <input type="number" value={it.contract_quantity} disabled={readOnly || busy}
                          onChange={e => recalc(i, e.target.value, undefined)}
                          className="input-field text-xs w-20" />
                      </td>
                      <td>
                        <input type="number" value={it.unit_price} disabled={readOnly || busy}
                          onChange={e => recalc(i, undefined, e.target.value)}
                          className="input-field text-xs w-20" />
                      </td>
                      <td className="num font-mono tabular-nums">{formatMoney(it.line_amount)}</td>
                      {!readOnly && (
                        <td>
                          <button onClick={() => setItems(items.filter((_, idx) => idx !== i))}
                            disabled={busy}
                            className="text-red-400 hover:text-red-600 text-xs">
                            删除
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr>
                      <td colSpan={readOnly ? 6 : 7}>
                        <EmptyState message="暂无项目行" />
                      </td>
                    </tr>
                  )}
                </tbody>
                {items.length > 0 && (
                  <tfoot>
                    <tr className="font-bold text-slate-800 border-t-2 border-slate-300">
                      <td colSpan={5} className="px-4 py-3 text-right">合计</td>
                      <td className="num px-4 py-3 font-mono tabular-nums">{formatMoney(itemsTotal)}</td>
                      {!readOnly && <td></td>}
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </Card>

          {validationErrors.length > 0 && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {validationErrors.map((e, i) => <div key={i}>• {e}</div>)}
            </div>
          )}

          {!readOnly && (
            <div className="mt-4 flex gap-2">
              <button onClick={() => openConfirm('save')} disabled={busy} className="btn-secondary">
                保存草稿
              </button>
              <button onClick={() => openConfirm('submit')} disabled={busy} className="btn-secondary">
                提交审核
              </button>
              <button onClick={() => openConfirm('approve')} disabled={busy} className="btn-primary">
                批准
              </button>
            </div>
          )}
        </div>
      </div>

      {confirm && (
        <ConfirmDialog
          title={confirm === 'approve' ? '批准合同版本' : confirm === 'submit' ? '提交审核' : '保存草稿'}
          message={
            confirm === 'approve'
              ? '批准后将锁定该版本，不可再编辑。确认批准？'
              : confirm === 'submit'
              ? '确认提交审核？'
              : '确认保存当前修改为草稿？'
          }
          confirmLabel={confirm === 'approve' ? '批准' : '确认'}
          onConfirm={() => doAction(confirm)}
          onCancel={() => setConfirm(null)}
        />
      )}
    </main>
  );
}
