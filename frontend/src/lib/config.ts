/** Resolved configuration from the environment (client-safe values only). */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/** Backend root (no /api/v1) — used for the OAuth full-page redirect. */
export const BACKEND_ROOT = API_URL.replace(/\/api\/v1\/?$/, "");
