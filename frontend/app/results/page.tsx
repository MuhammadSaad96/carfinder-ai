"use client";

import { useEffect, useState, useCallback, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { searchCars, type SearchResponse, type CarListing, type ModelInfo } from "@/lib/api";
import CarCard from "@/components/CarCard";
import LoadingSkeleton from "@/components/LoadingSkeleton";

// Each step: label, icon, time (s) when it typically completes, progress ceiling %
const STEPS = [
  { label: "Understanding your query",     icon: "🧠", doneAt: 2,  pct: 10 },
  { label: "Searching PakWheels listings", icon: "🔍", doneAt: 14, pct: 38 },
  { label: "Searching OLX Pakistan",       icon: "🏪", doneAt: 40, pct: 72 },
  { label: "Ranking results by relevance", icon: "📊", doneAt: 43, pct: 82 },
  { label: "Generating AI explanations",   icon: "✨", doneAt: 58, pct: 97 },
];

type Tab = "recommended" | "pakwheels" | "olx";

function ModelOverviewCard({ info, filters }: { info: ModelInfo; filters: Record<string, unknown> }) {
  const make = String(filters.make || "").replace(/\b\w/g, (c) => c.toUpperCase());
  const model = String(filters.model_name || "").replace(/\b\w/g, (c) => c.toUpperCase());
  const heading = make && model && model.toLowerCase() !== make.toLowerCase()
    ? `${make} ${model}`
    : make || "Model Overview";

  const stats = [
    info.new_price   && { icon: "🏷️", label: "New Price",    value: info.new_price },
    info.fuel_average && { icon: "⛽", label: "Fuel Average", value: info.fuel_average },
    info.engine       && { icon: "🔧", label: "Engine",       value: info.engine },
  ].filter(Boolean) as { icon: string; label: string; value: string }[];

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2 bg-slate-50">
        <span className="text-base">📋</span>
        <span className="text-xs font-bold uppercase tracking-widest text-slate-500">{heading} — Model Overview</span>
      </div>

      <div className="p-5 space-y-4">
        {/* Stats row */}
        {stats.length > 0 && (
          <div className={`grid gap-3 ${stats.length === 3 ? "grid-cols-3" : stats.length === 2 ? "grid-cols-2" : "grid-cols-1"}`}>
            {stats.map((s) => (
              <div key={s.label} className="bg-slate-50 rounded-xl p-3 border border-slate-100 text-center">
                <div className="text-lg mb-1">{s.icon}</div>
                <div className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold mb-0.5">{s.label}</div>
                <div className="text-sm font-bold text-slate-800 leading-tight">{s.value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Variants */}
        {info.variants && info.variants.length > 0 && (
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold mb-1.5">Available Variants</p>
            <div className="flex flex-wrap gap-1.5">
              {info.variants.map((v) => (
                <span key={v} className="text-xs px-2.5 py-1 bg-blue-50 text-blue-700 border border-blue-100 rounded-full font-medium">
                  {v}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Known for + Check before buy */}
        <div className="grid sm:grid-cols-2 gap-3">
          {info.known_for && (
            <div className="flex gap-2.5 bg-emerald-50 border border-emerald-100 rounded-xl p-3">
              <span className="text-base flex-shrink-0">✅</span>
              <div>
                <p className="text-[10px] text-emerald-600 font-bold uppercase tracking-wide mb-0.5">Known For</p>
                <p className="text-sm text-slate-700 leading-snug">{info.known_for}</p>
              </div>
            </div>
          )}
          {info.check_before_buy && (
            <div className="flex gap-2.5 bg-orange-50 border border-orange-100 rounded-xl p-3">
              <span className="text-base flex-shrink-0">⚠️</span>
              <div>
                <p className="text-[10px] text-orange-600 font-bold uppercase tracking-wide mb-0.5">Check Before Buying</p>
                <p className="text-sm text-slate-700 leading-snug">{info.check_before_buy}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultsPageInner() {
  const params = useSearchParams();
  const router = useRouter();
  const query = params.get("q") || "";

  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [stepIdx, setStepIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [newQuery, setNewQuery] = useState(query);
  const [tab, setTab] = useState<Tab>("recommended");
  const startRef = useRef<number>(0);
  const searchedRef = useRef<string>("");

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setData(null);
    setTab("recommended");
    setProgress(0);
    setStepIdx(0);
    setElapsed(0);
    startRef.current = Date.now();

    // Drive progress bar + step advancement from elapsed time
    const iv = setInterval(() => {
      const sec = (Date.now() - startRef.current) / 1000;
      setElapsed(Math.floor(sec));

      // Advance step based on elapsed time
      let step = 0;
      for (let i = 0; i < STEPS.length; i++) {
        if (sec >= STEPS[i].doneAt) step = i + 1;
      }
      setStepIdx(Math.min(step, STEPS.length - 1));

      // Smooth progress: ease toward current step's ceiling
      const ceiling = step < STEPS.length ? STEPS[step].pct : 97;
      setProgress((prev) => {
        const gap = ceiling - prev;
        return prev + Math.max(gap * 0.08, 0.3);
      });
    }, 400);

    try {
      setData(await searchCars(q));
      setProgress(100);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      clearInterval(iv);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (query && searchedRef.current !== query) {
      searchedRef.current = query;
      setNewQuery(query);
      doSearch(query);
    }
  }, [query, doSearch]);

  const go = (q: string) => {
    if (!q.trim()) return;
    router.push(`/results?q=${encodeURIComponent(q.trim())}`);
  };

  // Derive per-tab car lists
  const recommended: CarListing[] = data
    ? data.cars.filter((c) => c.is_recommended)
    : [];
  const pakwheelsCars: CarListing[] = data
    ? data.cars.filter((c) => c.source === "pakwheels")
    : [];
  const olxCars: CarListing[] = data
    ? data.cars.filter((c) => c.source === "olx")
    : [];
  const filtered: CarListing[] =
    tab === "recommended" ? recommended :
    tab === "pakwheels"   ? pakwheelsCars :
    olxCars;

  const tabs = [
    { id: "recommended" as Tab, label: "⭐ Top Recommended", count: recommended.length,   color: "amber" },
    { id: "pakwheels"   as Tab, label: "PakWheels",          count: pakwheelsCars.length, color: "emerald" },
    { id: "olx"         as Tab, label: "OLX",                count: olxCars.length,       color: "blue" },
  ];

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col">

      {/* Sticky Header */}
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 font-extrabold text-lg hover:opacity-75 transition-opacity flex-shrink-0 text-slate-900"
          >
            <span>🚗</span>
            <span className="hidden sm:inline">
              CarFinder<span className="text-orange-500">AI</span>
            </span>
          </button>

          <div className="flex-1 flex gap-2">
            <input
              type="text"
              value={newQuery}
              onChange={(e) => setNewQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && go(newQuery)}
              placeholder="Search again..."
              className="flex-1 bg-slate-50 border border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 rounded-lg px-4 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none transition-all"
            />
            <button
              onClick={() => go(newQuery)}
              disabled={loading}
              className="btn-primary px-5 py-2 rounded-lg text-sm flex items-center gap-1.5 disabled:opacity-40"
            >
              {loading
                ? <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                : <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
              }
              Search
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-6">

        {/* Loading */}
        {loading && (
          <div className="space-y-5">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              {/* Header */}
              <div className="px-6 pt-6 pb-4 border-b border-slate-100">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-xs text-slate-400 uppercase tracking-widest font-semibold">Searching for</p>
                  <span className="text-xs text-slate-400 tabular-nums">{elapsed}s elapsed</span>
                </div>
                <p className="text-slate-900 font-bold text-lg truncate">&ldquo;{query}&rdquo;</p>
              </div>

              <div className="px-6 py-5 space-y-5">
                {/* Progress bar */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-semibold text-slate-500">
                      {STEPS[Math.min(stepIdx, STEPS.length - 1)].label}
                      {stepIdx < STEPS.length && (
                        <span className="ml-1.5 inline-block w-3.5 h-3.5 border-2 border-blue-400/40 border-t-blue-500 rounded-full animate-spin align-middle" />
                      )}
                    </span>
                    <span className="text-xs font-bold text-blue-600 tabular-nums">
                      {Math.min(Math.round(progress), 99)}%
                    </span>
                  </div>
                  <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500 ease-out"
                      style={{
                        width: `${Math.min(progress, 99)}%`,
                        background: "linear-gradient(90deg, #10b981, #3b82f6, #8b5cf6)",
                        backgroundSize: "200% 100%",
                        animation: "shimmer-bar 2s linear infinite",
                      }}
                    />
                  </div>
                </div>

                {/* Step list */}
                <div className="space-y-2.5">
                  {STEPS.map((step, i) => {
                    const done = i < stepIdx;
                    const active = i === stepIdx;
                    return (
                      <div key={i} className={`flex items-center gap-3 transition-opacity duration-300 ${done || active ? "opacity-100" : "opacity-35"}`}>
                        {/* Indicator */}
                        <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                          done
                            ? "bg-emerald-100 text-emerald-600"
                            : active
                              ? "bg-blue-100 text-blue-600 ring-2 ring-blue-300 ring-offset-1"
                              : "bg-slate-100 text-slate-400"
                        }`}>
                          {done ? "✓" : active ? (
                            <span className="w-2.5 h-2.5 border-2 border-blue-400/40 border-t-blue-500 rounded-full animate-spin block" />
                          ) : String(i + 1)}
                        </div>
                        <span className={`text-sm ${done ? "text-slate-500 line-through decoration-slate-300" : active ? "text-slate-900 font-semibold" : "text-slate-400"}`}>
                          {step.icon} {step.label}
                        </span>
                        {done && <span className="ml-auto text-xs text-emerald-500 font-semibold">Done</span>}
                        {active && <span className="ml-auto text-xs text-blue-400 font-medium animate-pulse">In progress...</span>}
                      </div>
                    );
                  })}
                </div>

                <p className="text-slate-400 text-xs text-center pt-1">
                  Both marketplaces searched simultaneously · usually 30–55 seconds
                </p>
              </div>
            </div>

            <LoadingSkeleton />
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="flex flex-col items-center py-24 gap-4 text-center bg-white rounded-xl border border-slate-200">
            <span className="text-5xl">⚠️</span>
            <h2 className="text-xl font-bold text-slate-900">Search failed</h2>
            <p className="text-slate-500 text-sm max-w-md">{error}</p>
            <button onClick={() => doSearch(query)} className="btn-primary px-6 py-2.5 rounded-xl text-sm font-bold">
              Try Again
            </button>
          </div>
        )}

        {/* Results */}
        {data && !loading && (
          <div className="space-y-5 fade-up">

            {/* Query card + Urdu AI summary */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <div className="flex items-start justify-between flex-wrap gap-2 mb-3">
                <div>
                  <p className="text-slate-400 text-xs uppercase tracking-widest mb-0.5">Results for</p>
                  <h1 className="text-xl font-extrabold text-slate-900">&ldquo;{data.query}&rdquo;</h1>
                </div>
                {data.source === "demo" && (
                  <span className="text-xs px-3 py-1.5 rounded-full bg-orange-50 text-orange-600 border border-orange-200 self-start">
                    Demo data
                  </span>
                )}
              </div>

              {/* AI summary */}
              {data.ai_summary && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex gap-3">
                  <span className="text-xl flex-shrink-0">✨</span>
                  <p className="text-slate-700 text-sm leading-relaxed">{data.ai_summary}</p>
                </div>
              )}
            </div>

            {/* Model Overview card */}
            {data.model_info && Object.keys(data.model_info).length > 0 && (
              <ModelOverviewCard info={data.model_info} filters={data.filters} />
            )}

            {/* Three source tabs */}
            <div className="flex items-center gap-2 flex-wrap">
              {tabs.map((t) => {
                const activeStyles: Record<string, string> = {
                  amber:   "bg-amber-500 text-white border-amber-500",
                  emerald: "bg-emerald-600 text-white border-emerald-600",
                  blue:    "bg-blue-600 text-white border-blue-600",
                };
                const isActive = tab === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all border shadow-sm ${
                      isActive
                        ? activeStyles[t.color]
                        : "bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:text-slate-800"
                    }`}
                  >
                    {t.label}
                    <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${
                      isActive ? "bg-white/25 text-white" : "bg-slate-100 text-slate-500"
                    }`}>
                      {t.count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Tab description */}
            {tab === "recommended" && (
              <p className="text-slate-400 text-xs">
                Showing top {recommended.length} AI-recommended cars across all sources
              </p>
            )}
            {tab === "pakwheels" && (
              <p className="text-slate-400 text-xs">
                Showing {pakwheelsCars.length} listings from PakWheels
              </p>
            )}
            {tab === "olx" && (
              <p className="text-slate-400 text-xs">
                Showing {olxCars.length} listings from OLX Pakistan
              </p>
            )}

            {/* Empty state */}
            {filtered.length === 0 && (
              <div className="flex flex-col items-center py-20 gap-4 text-center bg-white rounded-xl border border-slate-200">
                <span className="text-5xl">🔍</span>
                <div>
                  <h2 className="text-lg font-bold text-slate-900 mb-1">
                    {data.total_found === 0
                      ? "No listings found"
                      : tab === "olx"       ? "No OLX listings found"
                      : tab === "pakwheels" ? "No PakWheels listings found"
                      : "No recommendations available"}
                  </h2>
                  <p className="text-slate-400 text-sm max-w-sm mx-auto">
                    {data.total_found === 0
                      ? "We searched PakWheels and OLX but found nothing matching your query. Try removing filters, checking the spelling, or searching a different city."
                      : tab === "recommended"
                        ? "Switch to PakWheels or OLX tabs to see all available listings."
                        : "Try searching without a specific city or check the other tab."}
                  </p>
                </div>
                {data.total_found === 0 && (
                  <div className="flex flex-wrap gap-2 justify-center">
                    {["Honda Civic in Lahore", "Toyota Corolla automatic", "Suzuki Alto cheap"].map((s) => (
                      <button
                        key={s}
                        onClick={() => go(s)}
                        className="text-xs px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-full border border-slate-200 transition-colors"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Card grid */}
            {filtered.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {filtered.map((car, i) => (
                  <CarCard key={`${car.url}-${i}`} car={car} index={i} />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense>
      <ResultsPageInner />
    </Suspense>
  );
}
