import { useSyncExternalStore } from "react";
import { setAuthTokenGetter } from "@workspace/api-client-react";

const KEY = "gantian.token";
let token: string | null = typeof localStorage !== "undefined" ? localStorage.getItem(KEY) : null;
const subs = new Set<() => void>();

setAuthTokenGetter(() => token);

export function setToken(t: string | null) {
  token = t;
  if (t) localStorage.setItem(KEY, t);
  else localStorage.removeItem(KEY);
  subs.forEach((f) => f());
}
export const getToken = () => token;
export function useToken() {
  return useSyncExternalStore((f) => { subs.add(f); return () => subs.delete(f); }, () => token);
}
