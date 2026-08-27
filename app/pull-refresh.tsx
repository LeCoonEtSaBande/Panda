"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

export function PullRefresh({
  onRefresh,
  children,
}: {
  onRefresh: () => void | Promise<void>;
  children: ReactNode;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const startY = useRef(0);
  const pulling = useRef(false);
  const offsetRef = useRef(0);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const onRefreshRef = useRef(onRefresh);
  onRefreshRef.current = onRefresh;

  const setOff = (n: number) => {
    offsetRef.current = n;
    setOffset(n);
  };

  const finish = useCallback(async () => {
    pulling.current = false;
    if (offsetRef.current > 56 && !busy) {
      setBusy(true);
      setOff(40);
      await onRefreshRef.current();
      setBusy(false);
    }
    setOff(0);
  }, [busy]);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;

    const start = (e: TouchEvent) => {
      if (el.scrollTop > 0) return;
      startY.current = e.touches[0].clientY;
      pulling.current = true;
    };
    const move = (e: TouchEvent) => {
      if (!pulling.current) return;
      if (el.scrollTop > 0) {
        pulling.current = false;
        setOff(0);
        return;
      }
      const dy = e.touches[0].clientY - startY.current;
      if (dy > 8) {
        e.preventDefault();
        setOff(Math.min(88, dy * 0.45));
      }
    };
    const stop = () => {
      void finish();
    };

    el.addEventListener("touchstart", start, { passive: true });
    el.addEventListener("touchmove", move, { passive: false });
    el.addEventListener("touchend", stop);
    el.addEventListener("touchcancel", stop);
    return () => {
      el.removeEventListener("touchstart", start);
      el.removeEventListener("touchmove", move);
      el.removeEventListener("touchend", stop);
      el.removeEventListener("touchcancel", stop);
    };
  }, [finish]);

  return (
    <div className="ptr" ref={scroller}>
      <div className="ptr-label" style={{ height: offset || (busy ? 40 : 0) }}>
        {busy ? "…" : offset > 56 ? "Relâche pour rafraîchir" : offset > 8 ? "↓" : ""}
      </div>
      {children}
    </div>
  );
}
