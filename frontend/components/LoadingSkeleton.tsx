export default function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <div className="h-48 shimmer" />
          <div className="p-4 space-y-3">
            <div className="h-4 shimmer rounded-lg w-3/4" />
            <div className="h-4 shimmer rounded-lg w-1/2" />
            <div className="h-7 shimmer rounded-lg w-2/5" />
            <div className="flex gap-2">
              <div className="h-6 shimmer rounded-full w-20" />
              <div className="h-6 shimmer rounded-full w-20" />
              <div className="h-6 shimmer rounded-full w-16" />
            </div>
            <div className="flex gap-2 pt-1">
              <div className="flex-1 h-10 shimmer rounded-lg" />
              <div className="w-16 h-10 shimmer rounded-lg" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
