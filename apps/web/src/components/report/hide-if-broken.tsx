"use client";

import { useEffect, useRef, useState } from "react";

/** Renders its children, and removes them if any image inside fails to load (e.g. a deleted file). */
export function HideIfBroken({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [broken, setBroken] = useState(false);
  useEffect(() => {
    const imgs = [...(ref.current?.querySelectorAll("img") ?? [])];
    // an image may have failed before hydration, so check the ones already settled too
    if (imgs.some((i) => i.complete && i.naturalWidth === 0)) setBroken(true);
    const onError = () => setBroken(true);
    imgs.forEach((i) => i.addEventListener("error", onError));
    return () => imgs.forEach((i) => i.removeEventListener("error", onError));
  }, []);
  if (broken) return null;
  return <div ref={ref}>{children}</div>;
}
