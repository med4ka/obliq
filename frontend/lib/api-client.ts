/**
 * Read-only client for the Obliq FastAPI layer.
 *
 * The frontend NEVER touches the database or external sources directly
 * (ARCHITECTURE.md §1). Every number shown comes from an API response, which
 * is the single consumer-facing gateway over the database.
 *
 * The API serializes Decimal values as exact strings (api/schemas.py) so
 * `yield_value`, `value`, etc. are kept as strings in the types below.
 * Callers convert with `toNumber()` only when a number is needed (e.g. chart
 * axes); display formatting is a separate concern.
 */

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

// Overridable so the app can point at any FastAPI backend. On the server this
// is read from the environment; on the client it must be a NEXT_PUBLIC_ var.
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_OBLIQ_API_BASE_URL ?? DEFAULT_API_BASE_URL
).replace(/\/+$/, "");

const REQUEST_TIMEOUT_MS = 15_000;

export class ApiClientError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiClientError";
  }
}

async function getJson<T>(path: string, params?: URLSearchParams): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    url.search = params.toString();
  }

  let resp: Response;
  try {
    resp = await fetch(url, {
      // Data is refreshed on the backend scheduler; never serve a stale build
      // copy of these numbers.
      cache: "no-store",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (err) {
    throw new ApiClientError(
      `API tidak bisa dijangkau (${url}). Pastikan \`uvicorn api.main:app\` sedang berjalan. Detail: ${String(err)}`
    );
  }

  if (!resp.ok) {
    throw new ApiClientError(
      `API mengembalikan status ${resp.status} untuk ${url}.`
    );
  }

  try {
    return (await resp.json()) as T;
  } catch (err) {
    throw new ApiClientError(
      `Respons API tidak valid JSON dari ${url}. Detail: ${String(err)}`
    );
  }
}

/* ------------------------- Shared item types ---------------------------- */

export interface MacroItem {
  indicator_type: string;
  observation_date: string;
  value: string;
  source: string;
  fetched_at: string;
  is_dummy: boolean;
  notice: string | null;
}

export interface YieldCurvePoint {
  bond_code: string;
  bond_name: string;
  tenor_years: string | null;
  coupon_rate: string | null;
  maturity_date: string | null;
  observation_date: string;
  yield_value: string;
  price: string | null;
  source: string;
  fetched_at: string;
  is_estimated: boolean;
}

export interface YieldHistoryItem {
  observation_date: string;
  yield_value: string;
  price: string | null;
  source: string;
  fetched_at: string;
  is_estimated: boolean;
}

/* ----------------------------- Responses -------------------------------- */

export type ApiStatus = "ok" | "empty" | "not_found";

export interface ApiListResponse<T> {
  status: ApiStatus;
  message: string | null;
  count: number;
  items: T[];
}

export interface MacroLatestResponse extends ApiListResponse<MacroItem> {
  status: "ok" | "empty";
}

export interface MacroHistoryResponse extends ApiListResponse<MacroItem> {
  status: "ok" | "empty";
  indicator_type: string;
  start: string | null;
  end: string | null;
}

export interface YieldCurveCurrentResponse extends ApiListResponse<YieldCurvePoint> {
  status: "ok" | "empty";
  as_of: string | null;
}

export interface YieldHistoryResponse extends ApiListResponse<YieldHistoryItem> {
  status: "ok" | "empty" | "not_found";
  bond_code: string;
  bond_name: string | null;
  start: string | null;
  end: string | null;
}

/* -------------------------- Stock / IHSG types ------------------------- */

export interface StockObservationItem {
  observation_date: string;
  open: string | null;
  high: string | null;
  low: string | null;
  close: string;
  adj_close: string | null;
  volume: number | null;
  source: string;
  fetched_at: string;
}

export interface StockHistoryResponse extends ApiListResponse<StockObservationItem> {
  status: "ok" | "empty";
  stock_code: string;
  start: string | null;
  end: string | null;
}

export interface StockLatestResponse {
  status: "ok" | "empty";
  message: string | null;
  stock_code: string;
  observation_date: string | null;
  close: string | null;
  adj_close: string | null;
  source: string | null;
  fetched_at: string | null;
}

export interface StockListItem {
  code: string;
  name: string;
  sector: string | null;
  kind: string;
  latest_close: string | null;
  latest_date: string | null;
  change: string | null;
  change_pct: string | null;
}

export interface StockListResponse {
  status: "ok" | "empty";
  message: string | null;
  count: number;
  items: StockListItem[];
}

/* ------------------------------ Helpers --------------------------------- */

/** Parse an API decimal string to a JS number. */
export function toNumber(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

/* --------------------------- Endpoint calls ----------------------------- */

export async function getCurrentCurve(): Promise<YieldCurveCurrentResponse> {
  return getJson<YieldCurveCurrentResponse>("/api/yield-curve/current");
}

/** Yield history of one bond code (e.g. FR0100), optionally bounded. */
export async function getBondHistory(
  bondCode: string,
  range?: { start?: string; end?: string }
): Promise<YieldHistoryResponse> {
  const params = new URLSearchParams({ bond_code: bondCode });
  if (range?.start) params.set("start", range.start);
  if (range?.end) params.set("end", range.end);
  return getJson<YieldHistoryResponse>("/api/yield-curve/history", params);
}

export async function getMacroLatest(): Promise<MacroLatestResponse> {
  return getJson<MacroLatestResponse>("/api/macro/latest");
}

/** Full history of one indicator, optionally bounded. */
export async function getMacroHistory(
  indicatorType: string,
  range?: { start?: string; end?: string }
): Promise<MacroHistoryResponse> {
  const params = new URLSearchParams();
  if (range?.start) params.set("start", range.start);
  if (range?.end) params.set("end", range.end);
  return getJson<MacroHistoryResponse>(
    `/api/macro/${encodeURIComponent(indicatorType)}`,
    params
  );
}

/* --------------------------- Stock / IHSG calls ------------------------- */

export async function getIhsgHistory(
  range?: { start?: string; end?: string }
): Promise<StockHistoryResponse> {
  const params = new URLSearchParams();
  if (range?.start) params.set("start", range.start);
  if (range?.end) params.set("end", range.end);
  return getJson<StockHistoryResponse>("/api/stocks/ihsg/history", params);
}

export async function getIhsgLatest(): Promise<StockLatestResponse> {
  return getJson<StockLatestResponse>("/api/stocks/ihsg/latest");
}

/* --------------------------- LQ45 stock calls --------------------------- */

export async function getStockList(): Promise<StockListResponse> {
  return getJson<StockListResponse>("/api/stocks/list");
}

/** History for one stock (e.g. BBCA), optionally ranged. */
export async function getStockHistory(
  ticker: string,
  range?: { start?: string; end?: string }
): Promise<StockHistoryResponse> {
  const params = new URLSearchParams();
  if (range?.start) params.set("start", range.start);
  if (range?.end) params.set("end", range.end);
  return getJson<StockHistoryResponse>(
    `/api/stocks/${encodeURIComponent(ticker)}/history`,
    params
  );
}

export async function getStockLatest(
  ticker: string
): Promise<StockLatestResponse> {
  return getJson<StockLatestResponse>(
    `/api/stocks/${encodeURIComponent(ticker)}/latest`
  );
}

/* ------------------------------ Auth calls ------------------------------- */

export interface AuthResponseData {
  status: string;
  message: string | null;
  user: { id: number; email: string } | null;
  access_token: string | null;
  refresh_token: string | null;
}

async function authFetch(path: string, body: unknown): Promise<AuthResponseData> {
  const resp = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  return resp.json() as Promise<AuthResponseData>;
}

export async function registerApi(email: string, password: string): Promise<AuthResponseData> {
  return authFetch("/api/auth/register", { email, password });
}

export async function loginApi(email: string, password: string): Promise<AuthResponseData> {
  return authFetch("/api/auth/login", { email, password });
}

export async function logoutApi(): Promise<AuthResponseData> {
  const resp = await fetch(`${API_BASE_URL}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  return resp.json() as Promise<AuthResponseData>;
}

export async function getMe(): Promise<AuthResponseData> {
  const resp = await fetch(`${API_BASE_URL}/api/auth/me`, {
    credentials: "include",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  return resp.json() as Promise<AuthResponseData>;
}

/* -------------------------- Watchlist calls ------------------------------ */

export interface WatchlistItemData {
  id: number;
  item_type: string;
  item_code: string;
  created_at: string;
}

export interface WatchlistResponseData {
  status: string;
  message: string | null;
  count: number;
  items: WatchlistItemData[];
}

async function watchlistFetch(path: string, options?: RequestInit): Promise<WatchlistResponseData> {
  const resp = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    ...options,
  });
  return resp.json() as Promise<WatchlistResponseData>;
}

export async function getWatchlist(): Promise<WatchlistResponseData> {
  return watchlistFetch("/api/watchlist");
}

export async function addWatchlist(itemType: string, itemCode: string): Promise<WatchlistResponseData> {
  return watchlistFetch("/api/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_type: itemType, item_code: itemCode }),
  });
}

export async function deleteWatchlist(itemId: number): Promise<WatchlistResponseData> {
  return watchlistFetch(`/api/watchlist/${itemId}`, { method: "DELETE" });
}
