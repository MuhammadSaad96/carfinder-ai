"use client";

import { useEffect, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import type { CarListing } from "@/lib/api";
import { API_URL } from "@/lib/api";

interface Props {
  car: CarListing;
  onClose: () => void;
}

function CarImage({ src, alt }: { src: string; alt: string }) {
  const [state, setState] = useState<"direct" | "proxy" | "error">("direct");
  const resolved =
    state === "direct" ? src :
    state === "proxy"  ? `${API_URL}/proxy-image?url=${encodeURIComponent(src)}` :
    null;

  const handleError = () => {
    if (state === "direct") setState("proxy");
    else setState("error");
  };

  if (!resolved || state === "error") {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
        <span className="text-8xl opacity-20">🚗</span>
      </div>
    );
  }
  return (
    <img
      key={src}
      src={resolved}
      alt={alt}
      referrerPolicy="no-referrer"
      className="w-full h-full object-cover"
      onError={handleError}
    />
  );
}

function PriceInsightFallback({ car }: { car: CarListing }) {
  const currentYear = new Date().getFullYear();
  const age = car.year ? currentYear - car.year : null;
  const isNew = car.mileage === null && (car.mileage_display?.toLowerCase().includes("new") || !car.mileage_display);

  const bullets: string[] = [];
  if (age !== null) {
    if (age === 0) bullets.push("Brand new model year — expect minimal wear.");
    else if (age === 1) bullets.push(`${car.year} model — 1 year old, likely still under manufacturer warranty.`);
    else if (age <= 3) bullets.push(`${car.year} model — ${age} years old, relatively recent with good resale value.`);
    else bullets.push(`${car.year} model — ${age} years old, verify service history and any major repairs.`);
  }
  if (isNew || car.mileage === 0) {
    bullets.push("Listed as new / zero meter — confirm actual odometer reading at delivery.");
  } else if (car.mileage) {
    const kmPerYear = age && age > 0 ? Math.round(car.mileage / age) : null;
    if (kmPerYear) {
      const label = kmPerYear < 8000 ? "very low usage" : kmPerYear < 14000 ? "normal usage" : "above-average usage";
      bullets.push(`${car.mileage.toLocaleString()} km total — roughly ${kmPerYear.toLocaleString()} km/year (${label}).`);
    }
  }
  bullets.push("Inspect engine, chassis, and accident history before finalising the deal.");

  return (
    <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
      <div className="flex items-center gap-2 mb-2.5">
        <span className="text-base">📊</span>
        <span className="text-slate-600 text-xs font-bold uppercase tracking-wide">Quick Buyer Checklist</span>
      </div>
      <ul className="space-y-1.5">
        {bullets.map((b, i) => (
          <li key={i} className="flex gap-2 text-sm text-slate-700 leading-snug">
            <span className="text-slate-400 flex-shrink-0 mt-0.5">•</span>
            {b}
          </li>
        ))}
      </ul>
    </div>
  );
}

function parseCondition(note: string | null | undefined) {
  if (!note) return null;
  const overallMatch = note.match(/Overall:\s*(\w+)/i);
  const overall = overallMatch?.[1] ?? null;
  const bullets = note
    .split("\n")
    .filter((l) => l.trim().startsWith("•"))
    .map((l) => {
      const clean = l.replace(/^•\s*/, "").trim();
      const colonIdx = clean.indexOf(":");
      return colonIdx > 0
        ? { label: clean.slice(0, colonIdx).trim(), value: clean.slice(colonIdx + 1).trim() }
        : { label: "", value: clean };
    });
  return { overall, bullets };
}

const OVERALL_STYLES: Record<string, { bar: string; badge: string; pct: string }> = {
  excellent: { bar: "bg-emerald-500", badge: "bg-emerald-100 text-emerald-700 border-emerald-200", pct: "100%" },
  good:      { bar: "bg-blue-500",    badge: "bg-blue-100 text-blue-700 border-blue-200",         pct: "72%"  },
  fair:      { bar: "bg-amber-500",   badge: "bg-amber-100 text-amber-700 border-amber-200",       pct: "45%"  },
  poor:      { bar: "bg-red-500",     badge: "bg-red-100 text-red-700 border-red-200",             pct: "20%"  },
};

const BULLET_ICONS: Record<string, string> = {
  paint: "🎨", body: "🚗", cleanliness: "✨", interior: "💺", verdict: "💡",
};

const SOURCE_LABEL: Record<string, string> = {
  pakwheels: "PakWheels",
  olx: "OLX Pakistan",
  gari: "Gari.pk",
};
const SOURCE_CLS: Record<string, string> = {
  pakwheels: "source-pw",
  olx: "source-olx",
  gari: "source-gari",
};
const LINK_CLS: Record<string, string> = {
  pakwheels: "bg-emerald-600 hover:bg-emerald-700",
  olx: "bg-blue-600 hover:bg-blue-700",
  gari: "bg-purple-600 hover:bg-purple-700",
};

export default function CarDetailModal({ car, onClose }: Props) {
  const condition  = parseCondition(car.condition_note);
  const [mounted, setMounted] = useState(false);
  const allImages  = car.images?.length ? car.images : (car.image ? [car.image] : []);
  const [imgIdx, setImgIdx]   = useState(0);
  const source     = car.source ?? "pakwheels";
  const hasMulti   = allImages.length > 1;

  useEffect(() => {
    setMounted(true);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight" && allImages.length > 1) setImgIdx((i) => (i + 1) % allImages.length);
      if (e.key === "ArrowLeft"  && allImages.length > 1) setImgIdx((i) => (i - 1 + allImages.length) % allImages.length);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose, allImages.length]);

  const prevImg = useCallback(() => setImgIdx((i) => (i - 1 + allImages.length) % allImages.length), [allImages.length]);
  const nextImg = useCallback(() => setImgIdx((i) => (i + 1) % allImages.length), [allImages.length]);

  if (!mounted) return null;

  const specs = [
    { label: "Year",         value: car.year,            icon: "📅" },
    { label: "City",         value: car.city,            icon: "📍" },
    { label: "Transmission", value: car.transmission,    icon: "⚙️" },
    { label: "Fuel Type",    value: car.fuel_type,       icon: "⛽" },
    { label: "Mileage",      value: car.mileage_display, icon: "🏎️" },
    { label: "Source",       value: SOURCE_LABEL[source] ?? source, icon: "🌐" },
  ].filter((s) => s.value);

  const modal = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 fade-in">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div
        className="relative z-10 bg-white rounded-2xl w-full max-w-2xl max-h-[92vh] overflow-y-auto shadow-2xl fade-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 sticky top-0 bg-white z-10">
          <div className="flex items-center gap-2">
            <span className={SOURCE_CLS[source] ?? "source-pw"}>
              {SOURCE_LABEL[source] ?? source}
            </span>
            {car.year && <span className="text-sm text-slate-400 font-medium">· {car.year}</span>}
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 hover:text-slate-800 text-sm transition-colors"
          >
            ✕
          </button>
        </div>

        {/* ── Main image carousel ── */}
        <div className="relative bg-slate-900 select-none" style={{ height: "320px" }}>
          {allImages.length > 0 ? (
            <CarImage src={allImages[imgIdx]} alt={car.title} />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <span className="text-8xl opacity-20">🚗</span>
            </div>
          )}

          {hasMulti && (
            <>
              <button onClick={prevImg}
                className="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 hover:bg-black/75 text-white flex items-center justify-center text-2xl leading-none transition-colors">
                ‹
              </button>
              <button onClick={nextImg}
                className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 hover:bg-black/75 text-white flex items-center justify-center text-2xl leading-none transition-colors">
                ›
              </button>
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-black/55 text-white text-xs font-semibold px-3 py-1 rounded-full">
                {imgIdx + 1} / {allImages.length}
              </div>
            </>
          )}
        </div>

        {/* ── Thumbnail strip ── */}
        {hasMulti && (
          <div className="flex gap-2 px-3 py-2.5 overflow-x-auto bg-slate-50 border-b border-slate-100 scrollbar-none">
            {allImages.map((img, i) => (
              <button
                key={i}
                onClick={() => setImgIdx(i)}
                className={`flex-shrink-0 w-16 h-11 rounded-lg overflow-hidden border-2 transition-all ${
                  i === imgIdx
                    ? "border-blue-500 opacity-100 scale-105"
                    : "border-transparent opacity-55 hover:opacity-85"
                }`}
              >
                <CarImage src={img} alt={`${i + 1}`} />
              </button>
            ))}
          </div>
        )}

        {/* ── Details ── */}
        <div className="p-5 space-y-4">

          {/* Title + price */}
          <div className="flex items-start justify-between gap-4">
            <h2 className="text-xl font-bold text-slate-900 leading-snug flex-1">{car.title}</h2>
            <div className="text-right flex-shrink-0">
              <div className="price-text">{car.price_display}</div>
            </div>
          </div>

          {/* Specs grid */}
          {specs.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {specs.map((s) => (
                <div key={s.label} className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                  <div className="text-[11px] text-slate-400 mb-0.5">{s.icon} {s.label}</div>
                  <div className="text-sm font-semibold text-slate-900">{String(s.value)}</div>
                </div>
              ))}
            </div>
          )}

          {/* AI explanation — prominent */}
          {car.ai_explanation ? (
            <div className="rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 p-4">
              <div className="flex items-center gap-2 mb-2.5">
                <span className="text-lg">✨</span>
                <span className="text-amber-700 text-xs font-bold uppercase tracking-wide">AI Buyer Analysis</span>
              </div>
              <p className="text-slate-800 text-sm leading-relaxed">{car.ai_explanation}</p>
            </div>
          ) : (
            <PriceInsightFallback car={car} />
          )}

          {/* AI Visual Inspection */}
          {!condition && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 flex items-center gap-3">
              <span className="text-base">🔍</span>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">AI Visual Inspection</p>
                <p className="text-xs text-slate-400 mt-0.5">Browse the photos above to assess paint, body and interior condition yourself.</p>
              </div>
            </div>
          )}
          {condition && (
            <div className="rounded-xl border border-slate-200 overflow-hidden">
              <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span>🔍</span>
                  <span className="text-slate-700 text-xs font-bold uppercase tracking-wide">AI Visual Inspection</span>
                </div>
                {condition.overall && OVERALL_STYLES[condition.overall.toLowerCase()] && (
                  <span className={`text-xs font-bold px-3 py-1 rounded-full border ${OVERALL_STYLES[condition.overall.toLowerCase()].badge}`}>
                    {condition.overall.charAt(0).toUpperCase() + condition.overall.slice(1).toLowerCase()} Condition
                  </span>
                )}
              </div>

              {condition.overall && OVERALL_STYLES[condition.overall.toLowerCase()] && (
                <div className="h-1.5 bg-slate-100">
                  <div
                    className={`h-full transition-all ${OVERALL_STYLES[condition.overall.toLowerCase()].bar}`}
                    style={{ width: OVERALL_STYLES[condition.overall.toLowerCase()].pct }}
                  />
                </div>
              )}

              <div className="divide-y divide-slate-100">
                {condition.bullets.map((b, i) => {
                  const icon = BULLET_ICONS[b.label.toLowerCase()] ?? "•";
                  const isVerdict = b.label.toLowerCase() === "verdict";
                  return (
                    <div key={i} className={`px-4 py-3 flex gap-3 ${isVerdict ? "bg-amber-50" : ""}`}>
                      <span className="text-base flex-shrink-0 mt-0.5">{icon}</span>
                      <div className="flex-1 min-w-0">
                        {b.label && (
                          <span className={`text-[11px] font-bold uppercase tracking-wide mr-1.5 ${isVerdict ? "text-amber-600" : "text-slate-400"}`}>
                            {b.label}
                          </span>
                        )}
                        <span className={`text-sm ${isVerdict ? "text-slate-800 font-medium" : "text-slate-600"}`}>
                          {b.value}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="px-4 py-2 bg-slate-50 border-t border-slate-100">
                <p className="text-[10px] text-slate-400">Based on listing photos · Always inspect in person before buying</p>
              </div>
            </div>
          )}

          {/* CTAs */}
          <div className="flex gap-3 pt-1">
            <a
              href={car.url}
              target="_blank"
              rel="noopener noreferrer"
              className={`flex-1 py-3 rounded-xl font-bold text-white text-center text-sm transition-colors ${LINK_CLS[source] ?? "bg-emerald-600 hover:bg-emerald-700"}`}
            >
              View on {SOURCE_LABEL[source] ?? source} ↗
            </a>
            <button
              onClick={onClose}
              className="px-6 py-3 rounded-xl btn-secondary font-semibold text-sm"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}
