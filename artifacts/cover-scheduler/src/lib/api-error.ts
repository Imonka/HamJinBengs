type MaybeApiError = { status?: number; data?: unknown; message?: string };

export function errStatus(e: unknown): number | undefined {
  return (e as MaybeApiError | null)?.status;
}
export function errMsg(e: unknown, fallback = "Something went wrong."): string {
  const d = (e as MaybeApiError | null)?.data;
  if (d && typeof d === "object" && "error" in d && typeof (d as { error: unknown }).error === "string") return (d as { error: string }).error;
  if (d && typeof d === "object" && "detail" in d) {
    const det = (d as { detail: unknown }).detail;
    if (typeof det === "string") return det;
  }
  return fallback;
}
export function errViolations(e: unknown): string[] {
  const d = (e as MaybeApiError | null)?.data;
  if (d && typeof d === "object" && Array.isArray((d as { violations?: unknown }).violations)) return (d as { violations: string[] }).violations;
  return [];
}
