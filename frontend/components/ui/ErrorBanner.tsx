'use client';

export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  return (
    <div className="flex items-center justify-between p-3 mb-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
      <span>{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="text-red-400 hover:text-red-600">✕</button>
      )}
    </div>
  );
}
