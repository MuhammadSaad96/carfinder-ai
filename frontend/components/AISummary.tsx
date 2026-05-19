interface AISummaryProps {
  summary: string;
  totalFound: number;
  source: string;
}

export default function AISummary({ summary, totalFound, source }: AISummaryProps) {
  return (
    <div className="relative rounded-2xl overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-purple-600/20 to-violet-600/20" />
      <div className="absolute inset-0 border border-purple-500/25 rounded-2xl" />
      <div className="relative p-5 flex items-start gap-4">
        <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-purple-600/30 flex items-center justify-center text-lg">
          ✨
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1.5">
            <span className="text-sm font-semibold text-purple-300">AI Summary</span>
            <span className="text-xs text-slate-500">
              {totalFound} car{totalFound !== 1 ? "s" : ""} found
              {source === "demo" && (
                <span className="ml-2 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/20">
                  Demo data
                </span>
              )}
            </span>
          </div>
          <p className="text-slate-200 text-sm leading-relaxed">{summary}</p>
        </div>
      </div>
    </div>
  );
}
