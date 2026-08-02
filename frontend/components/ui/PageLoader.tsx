export function PageLoader({ message = '加载中...' }: { message?: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500 mr-3"></div>
      <span className="text-slate-500 text-sm">{message}</span>
    </div>
  );
}
