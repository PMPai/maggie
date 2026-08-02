import { formatMoney } from './common';

export function MoneyCell({ value, className = '' }: { value: string | number | null | undefined; className?: string }) {
  return <td className={`num ${className}`}>{value === null || value === undefined || value === '' ? '—' : formatMoney(value)}</td>;
}
