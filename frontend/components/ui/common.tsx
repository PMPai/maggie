export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`card ${className}`}>{children}</div>;
}

export function CardHeader({ title, actions }: { title: string; actions?: React.ReactNode }) {
  return (
    <div className="card-header flex items-center justify-between">
      <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
      {actions}
    </div>
  );
}

export function StatCard({ label, value, icon, color = 'orange' }: { label: string; value: string | number; icon: string; color?: string }) {
  const colorMap: Record<string, string> = {
    orange: 'bg-orange-50 text-orange-600',
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-emerald-50 text-emerald-600',
    slate: 'bg-slate-100 text-slate-600',
    red: 'bg-red-50 text-red-600',
  };
  return (
    <div className="stat-card">
      <div className={`stat-icon ${colorMap[color] || colorMap.orange}`}>
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
        </svg>
      </div>
      <div>
        <p className="stat-label">{label}</p>
        <p className="stat-value">{value}</p>
      </div>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const statusMap: Record<string, { class: string; label: string }> = {
    DRAFT: { class: 'badge-gray', label: '草稿' },
    SUBMITTED: { class: 'badge-blue', label: '已提交' },
    PROJECT_APPROVED: { class: 'badge-blue', label: '项目已审' },
    FINANCE_APPROVED: { class: 'badge-blue', label: '财务已审' },
    POSTED: { class: 'badge-green', label: '已过账' },
    GENERATED: { class: 'badge-green', label: '已生成' },
    SENT: { class: 'badge-green', label: '已发送' },
    REJECTED: { class: 'badge-red', label: '已拒绝' },
    CANCELLED: { class: 'badge-gray', label: '已取消' },
    SUPERSEDED: { class: 'badge-gray', label: '已替代' },
    APPROVED: { class: 'badge-green', label: '已批准' },
    UNDER_REVIEW: { class: 'badge-yellow', label: '审核中' },
    ACTIVE: { class: 'badge-green', label: '活跃' },
    ISSUED: { class: 'badge-blue', label: '已开票' },
    PAID: { class: 'badge-green', label: '已付清' },
    PARTIALLY_PAID: { class: 'badge-yellow', label: '部分付款' },
    VOID: { class: 'badge-gray', label: '已作废' },
    PENDING: { class: 'badge-yellow', label: '待处理' },
    CONFIRMED: { class: 'badge-green', label: '已确认' },
    DRAFT_INVOICE: { class: 'badge-gray', label: '草稿' },
  };
  const config = statusMap[status] || { class: 'badge-gray', label: status };
  return <span className={`badge ${config.class}`}>{config.label}</span>;
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <svg className="w-12 h-12 text-slate-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p className="text-sm text-slate-400">{message}</p>
    </div>
  );
}

export function formatMoney(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';
  return num.toLocaleString('zh-TW', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

export function formatNumber(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';
  return num.toLocaleString('zh-TW', { minimumFractionDigits: 0, maximumFractionDigits: 4 });
}
