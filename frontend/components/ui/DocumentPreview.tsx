'use client';
import { useState } from 'react';

export function DocumentPreview({ documentId, className = '' }: { documentId: string; className?: string }) {
  const [loading, setLoading] = useState(true);
  const url = `/api/documents/${documentId}/preview`;
  return (
    <div className={`relative border border-slate-200 rounded-lg overflow-hidden bg-slate-50 ${className}`}>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
        </div>
      )}
      <iframe
        src={url}
        className="w-full h-full min-h-[500px]"
        onLoad={() => setLoading(false)}
        title="document-preview"
      />
    </div>
  );
}
