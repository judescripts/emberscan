"use client";

import { useState } from "react";

/** The zone map's SVG with a zoom toggle: all zones (default) or zoomed to the hazards. */
export function ZoomableMap({
  fullView,
  fitView,
  children,
}: {
  fullView: string;
  fitView: string;
  children: React.ReactNode;
}) {
  const [zoomed, setZoomed] = useState(false);
  const canZoom = fitView !== fullView;
  return (
    <div className="relative mx-auto w-full max-w-md">
      <svg
        viewBox={zoomed ? fitView : fullView}
        className="w-full rounded-xl transition-[viewBox]"
        role="img"
        aria-labelledby="zonemap-title zonemap-desc"
      >
        {children}
      </svg>
      <div className="pointer-events-none absolute top-2 right-2 flex flex-col items-center text-[11px] font-bold text-ink" aria-hidden>
        N
        <svg viewBox="0 0 8 9" className="h-2.5 w-2.5">
          <path d="M4 0 L0 9 H8 Z" fill="currentColor" />
        </svg>
      </div>
      {canZoom && (
        <button
          type="button"
          onClick={() => setZoomed((z) => !z)}
          aria-pressed={zoomed}
          className="absolute bottom-2 left-2 rounded-full border border-line bg-surface/95 px-3 py-1.5 text-xs font-semibold text-ink shadow-sm hover:bg-soft"
        >
          {zoomed ? "Zoom out: all zones" : "Zoom in"}
        </button>
      )}
    </div>
  );
}
