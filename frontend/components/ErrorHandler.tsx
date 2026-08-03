'use client';
import React from 'react';

interface State { hasError: boolean; message: string; }

export class ErrorHandler extends React.Component<{ children: React.ReactNode }, State> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('App error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
          <div className="bg-white rounded-lg p-8 max-w-md w-full text-center shadow-lg">
            <div className="w-14 h-14 rounded-xl bg-orange-500 flex items-center justify-center text-white font-bold text-2xl mx-auto mb-4">M</div>
            <h1 className="text-lg font-semibold text-slate-800 mb-2">页面加载异常</h1>
            <p className="text-sm text-slate-500 mb-4">
              系统遇到客户端渲染错误。请刷新页面重试。如问题持续，请清除浏览器缓存后重试。
            </p>
            <pre className="text-xs text-red-500 bg-red-50 p-3 rounded mb-4 overflow-auto max-h-32">{this.state.message}</pre>
            <button
              onClick={() => { this.setState({ hasError: false, message: '' }); window.location.reload(); }}
              className="btn-primary"
            >
              刷新页面
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
