

export function ErrorFallback({ error, resetErrorBoundary }: any) {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-slate-100 font-sans">
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 max-w-lg w-full shadow-2xl backdrop-blur">
        <div className="w-12 h-12 bg-red-900/30 border border-red-800/50 rounded-xl flex items-center justify-center mb-5">
           <span className="text-red-400 font-bold text-xl">!</span>
        </div>
        <h2 className="text-xl font-bold text-slate-100 mb-2">Something went wrong!</h2>
        <p className="text-sm text-slate-400 mb-6 leading-relaxed">
          An unexpected error caused the application interface to crash. You can try recovering the session by hitting the button below.
        </p>
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 mb-6 overflow-auto max-h-40 shadow-inner">
           <pre className="text-[11px] text-red-400 font-mono whitespace-pre-wrap">{error.message}</pre>
        </div>
        <button
          onClick={resetErrorBoundary}
          className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 px-4 rounded-xl transition-colors shadow-sm"
        >
          Reload Session
        </button>
      </div>
    </div>
  );
}
