"use client";

import { useState } from "react";
import type { CarListing } from "@/lib/api";
import { API_URL } from "@/lib/api";
import CarDetailModal from "./CarDetailModal";

interface Props {
  car: CarListing;
  index: number;
}

export default function CarCard({ car, index }: Props) {
  const [showModal, setShowModal] = useState(false);
  const [imgIdx, setImgIdx]       = useState(0);
  const [imgProxy, setImgProxy]   = useState(false);
  const [imgError, setImgError]   = useState(false);
  const [hovered, setHovered]     = useState(false);

  const source    = car.source ?? "pakwheels";
  const isOlx     = source === "olx";
  const allImages = car.images?.length ? car.images : (car.image ? [car.image] : []);
  const hasMulti  = allImages.length > 1;

  const conditionRating = car.condition_note
    ? (car.condition_note.match(/Overall:\s*(\w+)/i)?.[1] ?? null)
    : null;
  const COND: Record<string, { cls: string; icon: string }> = {
    excellent: { cls: "bg-emerald-500 text-white", icon: "★" },
    good:      { cls: "bg-blue-500 text-white",    icon: "✓" },
    fair:      { cls: "bg-amber-500 text-white",   icon: "~" },
    poor:      { cls: "bg-red-500 text-white",     icon: "!" },
  };
  const condBadge = conditionRating ? COND[conditionRating.toLowerCase()] : null;

  const currentSrc = allImages[imgIdx] ?? null;
  const imgSrc = currentSrc
    ? imgProxy
      ? `${API_URL}/proxy-image?url=${encodeURIComponent(currentSrc)}`
      : currentSrc
    : null;

  const handleImgError = () => {
    if (!imgProxy) setImgProxy(true);
    else setImgError(true);
  };

  const changeImg = (newIdx: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setImgIdx(newIdx);
    setImgProxy(false);
    setImgError(false);
  };

  const SOURCE_LABEL: Record<string, string> = {
    pakwheels: "PakWheels",
    olx: "OLX",
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

  const visibleDots = Math.min(allImages.length, 6);

  return (
    <>
      <div
        className="car-card flex flex-col cursor-pointer fade-up"
        style={{ animationDelay: `${index * 40}ms` }}
        onClick={() => setShowModal(true)}
      >
        {/* ── Image area ── */}
        <div
          className="relative h-52 overflow-hidden bg-slate-100 flex-shrink-0"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          {!imgError && imgSrc ? (
            <img
              key={currentSrc}
              src={imgSrc}
              alt={car.title}
              referrerPolicy="no-referrer"
              className="w-full h-full object-cover transition-transform duration-500 hover:scale-105"
              onError={handleImgError}
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
              <span className="text-5xl mb-2 opacity-20">🚗</span>
              <span className="text-xs text-slate-400 font-medium">
                {car.title.split(" ").slice(0, 3).join(" ")}
              </span>
            </div>
          )}

          {/* Source badge */}
          <div className="absolute top-2.5 left-2.5">
            <span className={SOURCE_CLS[source] ?? "source-pw"}>
              {SOURCE_LABEL[source] ?? source}
            </span>
          </div>

          {/* Year badge */}
          {car.year && (
            <div className="absolute top-2.5 right-2.5 bg-black/60 text-white text-xs font-bold px-2 py-0.5 rounded-md">
              {car.year}
            </div>
          )}

          {/* Condition badge */}
          {condBadge && conditionRating && (
            <span className={`absolute bottom-2.5 left-2.5 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide shadow ${condBadge.cls}`}>
              {condBadge.icon} {conditionRating}
            </span>
          )}

          {/* Carousel arrows — shown on hover */}
          {hasMulti && hovered && (
            <>
              <button
                onClick={(e) => changeImg((imgIdx - 1 + allImages.length) % allImages.length, e)}
                className="absolute left-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/55 hover:bg-black/75 text-white flex items-center justify-center text-lg leading-none transition-colors shadow"
                aria-label="Previous"
              >
                ‹
              </button>
              <button
                onClick={(e) => changeImg((imgIdx + 1) % allImages.length, e)}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/55 hover:bg-black/75 text-white flex items-center justify-center text-lg leading-none transition-colors shadow"
                aria-label="Next"
              >
                ›
              </button>
            </>
          )}

          {/* Dot indicators */}
          {hasMulti && (
            <div className="absolute bottom-2.5 right-2.5 flex items-center gap-1">
              {Array.from({ length: visibleDots }).map((_, i) => (
                <button
                  key={i}
                  onClick={(e) => changeImg(i, e)}
                  className={`rounded-full transition-all ${
                    i === imgIdx
                      ? "w-4 h-1.5 bg-white"
                      : "w-1.5 h-1.5 bg-white/50 hover:bg-white/80"
                  }`}
                  aria-label={`Image ${i + 1}`}
                />
              ))}
              {allImages.length > 6 && (
                <span className="text-white/70 text-[10px] font-semibold ml-0.5">
                  +{allImages.length - 6}
                </span>
              )}
            </div>
          )}
        </div>

        {/* ── Content ── */}
        <div className="p-4 flex flex-col flex-1 gap-2.5">

          {/* Title */}
          <h3 className="text-slate-900 font-semibold text-sm leading-snug line-clamp-2">
            {car.title}
          </h3>

          {/* Price */}
          <div className="price-text">{car.price_display}</div>

          {/* Key specs — compact row */}
          <div className="flex flex-wrap gap-1.5">
            {car.city         && <span className="spec-chip">📍 {car.city}</span>}
            {car.mileage_display && <span className="spec-chip">🏎️ {car.mileage_display}</span>}
            {car.transmission && <span className="spec-chip">⚙️ {car.transmission}</span>}
            {car.fuel_type    && <span className="spec-chip">⛽ {car.fuel_type}</span>}
          </div>

          {/* AI insight box */}
          {car.ai_explanation && (
            <div className="mt-auto bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-3">
              <div className="flex gap-2">
                <span className="text-amber-500 flex-shrink-0 mt-0.5">✨</span>
                <p className="text-slate-700 text-xs leading-relaxed line-clamp-3">
                  {car.ai_explanation}
                </p>
              </div>
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-2 pt-0.5 mt-auto">
            <button
              onClick={(e) => { e.stopPropagation(); setShowModal(true); }}
              className="flex-1 py-2.5 rounded-xl btn-secondary text-sm font-semibold"
            >
              Full Details
            </button>
            <a
              href={car.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className={`px-4 py-2.5 rounded-xl text-white text-sm font-semibold flex items-center gap-1 transition-colors ${LINK_CLS[source] ?? "bg-emerald-600 hover:bg-emerald-700"}`}
            >
              {SOURCE_LABEL[source]?.split(" ")[0] ?? "View"} <span className="text-xs">↗</span>
            </a>
          </div>
        </div>
      </div>

      {showModal && (
        <CarDetailModal car={car} onClose={() => setShowModal(false)} />
      )}
    </>
  );
}
