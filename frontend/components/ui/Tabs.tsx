'use client';

export interface TabItem { key: string; label: string; }

export function Tabs({ tabs, active, onChange }: {
  tabs: TabItem[];
  active: string;
  onChange: (key: string) => void;
}) {
  return (
    <div className="flex gap-1 border-b border-slate-200 mb-6 overflow-x-auto">
      {tabs.map(t => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={`px-4 py-2.5 text-sm whitespace-nowrap ${active === t.key ? 'tab-active' : 'tab-inactive'}`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
