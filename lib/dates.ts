/** Date du jour à Paris, format YYYY-MM-DD. */
export function todayISO(timeZone = "Europe/Paris"): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

/** Si Claude date en 2025 (ou une année déjà passée), on recale sur l’année en cours. */
export function coerceDueAt(
  raw: string | null | undefined,
  today: string,
): string | null {
  const due = (raw ?? "").trim();
  if (!due) return null;
  const m = due.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return due;
  const todayYear = Number(today.slice(0, 4));
  const year = Number(m[1]);
  if (year >= todayYear) return due;
  return `${todayYear}-${m[2]}-${m[3]}`;
}
