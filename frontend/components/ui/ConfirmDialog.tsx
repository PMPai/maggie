'use client';
import { useState } from 'react';

export function ConfirmDialog({ title, message, confirmLabel = '确认', cancelLabel = '取消', onConfirm, onCancel, requireReason = false }: {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: (reason?: string) => void;
  onCancel: () => void;
  requireReason?: boolean;
}) {
  const [reason, setReason] = useState('');
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-semibold text-slate-800 mb-2">{title}</h3>
        <p className="text-sm text-slate-600 mb-4">{message}</p>
        {requireReason && (
          <input
            type="text"
            placeholder="请输入原因..."
            value={reason}
            onChange={e => setReason(e.target.value)}
            className="input-field text-sm w-full mb-4"
          />
        )}
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="btn-secondary">{cancelLabel}</button>
          <button
            onClick={() => onConfirm(requireReason ? reason : undefined)}
            className="btn-primary"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
