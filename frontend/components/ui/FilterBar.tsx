'use client';

export interface FilterOption { label: string; value: string; }
export interface FilterDef {
  label: string;
  value: string;
  options: FilterOption[];
  onChange: (v: string) => void;
}

export function FilterBar({ filters, searchValue, onSearchChange }: {
  filters: FilterDef[];
  searchValue?: string;
  onSearchChange?: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-4 p-3 bg-white border border-slate-200 rounded-lg">
      {filters.map(f => (
        <div key={f.label} className="flex items-center gap-2">
          <label className="text-xs text-slate-500">{f.label}</label>
          <select
            value={f.value}
            onChange={e => f.onChange(e.target.value)}
            className="input-field text-sm py-1.5"
          >
            <option value="">全部</option>
            {f.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      ))}
      {searchValue !== undefined && onSearchChange && (
        <input
          type="text"
          placeholder="搜索..."
          value={searchValue}
          onChange={e => onSearchChange(e.target.value)}
          className="input-field text-sm py-1.5 ml-auto w-64"
        />
      )}
    </div>
  );
}
