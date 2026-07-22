import './globals.css';
import type { Metadata } from 'next';
import { AppShell } from '@/components/AppShell';

export const metadata: Metadata = {
  title: '工程合同及请款管理系统',
  description: 'Engineering Contract & Payment Application Management System',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-slate-50 text-slate-700 antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
