export const TZ = "Asia/Kuala_Lumpur";

const f = (opts: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("en-MY", { timeZone: TZ, ...opts });
const timeF = f({ hour: "numeric", minute: "2-digit", hour12: true });
const dayF = f({ weekday: "short", day: "numeric", month: "short" });
const dateF = f({ day: "numeric", month: "short", year: "numeric" });
const keyF = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
const hmF = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: false });

export const fmtTime = (iso: string) => timeF.format(new Date(iso)).replace(" ", "").toLowerCase();
export const fmtDay = (iso: string) => dayF.format(new Date(iso));
export const fmtDateTime = (iso: string) => `${fmtDay(iso)}, ${fmtTime(iso)}`;
export const fmtRange = (a: string, b: string) => `${fmtDay(a)} · ${fmtTime(a)} to ${fmtTime(b)}`;
/** YYYY-MM-DD -> readable */
export const fmtDate = (ymd: string) => dateF.format(new Date(ymd.length === 10 ? `${ymd}T12:00:00+08:00` : ymd));
export const klDateKey = (d: Date | string) => keyF.format(typeof d === "string" ? new Date(d) : d);
export const todayKey = () => klDateKey(new Date());
export const hoursBetween = (a: string, b: string) => (new Date(b).getTime() - new Date(a).getTime()) / 36e5;

export function addDays(ymd: string, n: number) {
  const d = new Date(`${ymd}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
export function mondayOf(ymd: string) {
  const dow = new Date(`${ymd}T12:00:00Z`).getUTCDay();
  return addDays(ymd, -((dow + 6) % 7));
}
export const klStartIso = (ymd: string) => new Date(`${ymd}T00:00:00+08:00`).toISOString();
/** datetime-local (KL wall time) -> ISO */
export const localToIso = (v: string) => new Date(`${v}:00+08:00`).toISOString();
/** ISO -> datetime-local in KL */
export const isoToLocal = (iso: string) => `${klDateKey(iso)}T${hmF.format(new Date(iso))}`;

export function relative(iso: string) {
  const diff = (new Date(iso).getTime() - Date.now()) / 60000;
  const abs = Math.abs(diff);
  const s = abs < 60 ? `${Math.round(abs)}m` : abs < 1440 ? `${Math.round(abs / 60)}h` : `${Math.round(abs / 1440)}d`;
  return diff >= 0 ? `in ${s}` : `${s} ago`;
}
export const initials = (n: string) => n.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
/** 0 = Monday */
export const weekdayOf = (ymd: string) => (new Date(`${ymd}T12:00:00Z`).getUTCDay() + 6) % 7;
const ymdF = new Intl.DateTimeFormat("en-MY", { timeZone: "UTC", weekday: "short", day: "numeric", month: "short" });
export const fmtYmd = (ymd: string) => ymdF.format(new Date(`${ymd}T12:00:00Z`));
/** "07:00" -> "7:00am" */
export function fmtHm(hm: string) {
  const [h, m] = hm.split(":").map(Number);
  const ap = h >= 12 && h < 24 ? "pm" : "am";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${hh}:${String(m).padStart(2, "0")}${ap}`;
}
export const fmtShift = (s: { date: string; startTime: string; endTime: string }) => `${fmtYmd(s.date)} · ${fmtHm(s.startTime)} to ${fmtHm(s.endTime)}`;
export function hmHours(a: string, b: string) {
  const t = (x: string) => { const [h, m] = x.split(":").map(Number); return h * 60 + m; };
  let d = t(b) - t(a); if (d <= 0) d += 1440;
  return d / 60;
}
