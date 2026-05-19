"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const PROMPTS = [
  "Honda City automatic under 30 lakh",
  "Toyota Corolla 2020 or newer Islamabad",
  "Suzuki Alto low mileage under 15 lakh",
  "Family SUV under 60 lakh Lahore",
  "Honda Civic reborn 2006 manual",
  "Fuel efficient car under 20 lakh Karachi",
];

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const go = (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    router.push(`/results?q=${encodeURIComponent(q.trim())}`);
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-slate-900 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl">🚗</span>
          <span className="font-extrabold text-xl tracking-tight text-white">
            CarFinder<span className="text-orange-400">AI</span>
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="source-pw">PakWheels</span>
          <span className="text-slate-500 font-bold">+</span>
          <span className="source-olx">OLX</span>
        </div>
      </header>

      {/* Hero */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-blue-950 py-16 sm:py-24 px-4">
        <div className="max-w-3xl mx-auto text-center space-y-7">
          <div className="inline-flex items-center gap-2 bg-orange-500/15 border border-orange-500/25 rounded-full px-4 py-1.5 text-orange-400 text-sm font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse" />
            Live data from PakWheels &amp; OLX Pakistan
          </div>

          <div>
            <h1 className="text-4xl sm:text-5xl font-extrabold leading-tight text-white mb-3">
              Find Your Perfect Car<br />
              <span className="text-orange-400">Across Pakistan</span>
            </h1>
            <p className="text-slate-300 text-lg">
              Describe what you want in <strong className="text-white">English or Urdu</strong> — AI searches both marketplaces instantly
            </p>
          </div>

          {/* Search bar */}
          <div className="flex gap-2 bg-white rounded-xl p-2 shadow-2xl shadow-black/40">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && go(query)}
              placeholder='e.g. "Automatic Honda City under 30 lakh Islamabad"'
              disabled={loading}
              autoFocus
              className="flex-1 text-slate-900 placeholder-slate-400 px-4 py-3 text-base focus:outline-none bg-transparent"
            />
            <button
              onClick={() => go(query)}
              disabled={loading || !query.trim()}
              className="btn-primary px-7 py-3 rounded-lg flex items-center gap-2 whitespace-nowrap disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              )}
              {loading ? "Searching..." : "Search Cars"}
            </button>
          </div>

          {/* Example queries */}
          <div>
            <p className="text-slate-500 text-xs uppercase tracking-widest mb-3">Popular searches</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => go(p)}
                  disabled={loading}
                  className="text-xs px-3.5 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white border border-white/15 hover:border-white/30 transition-all disabled:opacity-40"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Stats strip */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 py-5 grid grid-cols-3 divide-x divide-slate-100 text-center">
          {[
            { n: "60,000+", label: "Live Listings" },
            { n: "2 Platforms", label: "PakWheels + OLX" },
            { n: "AI Ranked", label: "Groq Llama Powered" },
          ].map((s) => (
            <div key={s.label} className="px-4">
              <div className="text-blue-600 font-extrabold text-xl">{s.n}</div>
              <div className="text-slate-500 text-xs mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Feature cards */}
      <div className="flex-1 py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-xl font-bold text-slate-900 text-center mb-8">Why CarFinderAI?</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            {[
              {
                icon: "🔍",
                title: "Natural Language Search",
                desc: "Search in plain English or Urdu — our AI understands budget, city, make, model, year and more.",
              },
              {
                icon: "⚡",
                title: "Two Marketplaces at Once",
                desc: "Get results from PakWheels AND OLX side by side — no need to switch between sites.",
              },
              {
                icon: "🤖",
                title: "AI Rankings & Explanations",
                desc: "Every listing is scored and explained by AI based on your exact search criteria.",
              },
            ].map((f) => (
              <div key={f.title} className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="font-bold text-slate-900 mb-2 text-sm">{f.title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
