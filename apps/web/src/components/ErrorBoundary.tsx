// Top-level error boundary: a thrown render error shows a calm, bilingual
// recovery card instead of a blank white screen. Kept language-agnostic (both
// AR + EN) because it sits above the App's language state.

import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface for diagnostics; no telemetry is sent.
    console.error("AgroVision render error:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div
        dir="rtl"
        className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#061a15] px-6 text-center text-emerald-50"
      >
        <div className="max-w-md rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <p className="text-lg font-bold">حصل خطأ غير متوقّع</p>
          <p className="mt-1 text-sm text-emerald-200/60">
            جرّب تعيد تحميل الصفحة. بياناتك المحلية ما اتمسحتش.
          </p>
          <hr className="my-4 border-white/10" />
          <p className="text-lg font-bold" dir="ltr">
            Something went wrong
          </p>
          <p className="mt-1 text-sm text-emerald-200/60" dir="ltr">
            Please reload the page. Your local data was not lost.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-5 rounded-xl bg-emerald-400 px-5 py-2.5 text-sm font-bold text-emerald-950 hover:bg-emerald-300"
          >
            إعادة التحميل · Reload
          </button>
        </div>
      </div>
    );
  }
}
