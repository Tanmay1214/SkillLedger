/**
 * Shared auth-related types. These mirror the Pydantic schemas in the backend
 * (`app/schemas/*`) and are the single source of truth for the API contract
 * on the frontend.
 */

/** Public user shape — identical to backend `UserPublic`. Never includes token. */
export interface User {
  id: number;
  github_id: number;
  username: string;
  name: string | null;
  email: string | null;
  avatar_url: string | null;
  profile_url: string | null;
  created_at: string;
  updated_at: string;
}

/** Response of `GET /auth/github/login`. */
export interface AuthUrlResponse {
  authorization_url: string;
  state: string;
}

/** Response of `GET /auth/github/callback`. */
export interface CallbackSuccess {
  user: User;
  redirect_to: string;
}

/** Standardized error body returned by the backend on auth failures. */
export interface ApiErrorResponse {
  detail: string;
  error_code: string | null;
}

/** Coarse lifecycle states for the auth context. */
export type AuthStatus = "loading" | "authenticated" | "unauthenticated";
