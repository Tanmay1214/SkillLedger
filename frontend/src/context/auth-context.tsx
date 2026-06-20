"use client";

/**
 * Authentication context — React Context API.
 *
 * WHY CONTEXT (not Zustand / Redux)?
 *  - The auth state is small (a User + status) and changes infrequently.
 *  - It is consumed widely (components, route guards, middleware hooks) but
 *    the *write* surface is tiny (login/logout/refresh) and centralized here.
 *  - Adding a store (Zustand) would mean another dependency, persistence
 *    glue, and devtools for a problem Context already solves cleanly.
 *  - The `credentials: "include"` cookie model means there is *no* token to
 *    hydrate into a store on mount — the session lives in an httpOnly cookie,
 *    so we just call `/auth/me` once. This is a natural fit for Context.
 *
 * For app-wide, high-frequency, derived state (e.g. a future repo-analysis
 * cache), Zustand would be a better choice. We'd layer it *on top* of this
 * context rather than replace it.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { apiClient, ApiError } from "@/lib/api-client";
import { BACKEND_ROOT } from "@/lib/config";
import type { AuthStatus, User } from "@/types/auth";

interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  /** True while a login redirect to GitHub is in flight. */
  loginInProgress: boolean;
  /** Error from the last login attempt, if any. */
  loginError: string | null;
  /** Kick off GitHub OAuth by redirecting the browser to the backend. */
  loginWithGithub: () => Promise<void>;
  /** Clear the session and notify the backend. */
  logout: () => Promise<void>;
  /** Force a re-fetch of the current user. */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [loginInProgress, setLoginInProgress] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const mounted = useRef(true);

  const refreshUser = useCallback(async () => {
    try {
      const me = await apiClient.getMe();
      if (!mounted.current) return;
      setUser(me);
      setStatus("authenticated");
    } catch (err) {
      if (!mounted.current) return;
      if (err instanceof ApiError && err.status === 401) {
        setUser(null);
        setStatus("unauthenticated");
      } else {
        // Network/server error — keep user signed-out but surface nothing.
        setUser(null);
        setStatus("unauthenticated");
      }
    }
  }, []);

  // Resolve the session once on mount (cookie-based, no token in JS).
  useEffect(() => {
    mounted.current = true;
    void refreshUser();
    return () => {
      mounted.current = false;
    };
  }, [refreshUser]);

  const loginWithGithub = useCallback(async () => {
    setLoginError(null);
    setLoginInProgress(true);
    try {
      const { authorization_url } = await apiClient.getLoginUrl();
      // Full-page redirect: the backend sets the CSRF state cookie, GitHub
      // bounces back to the backend callback, which then redirects here.
      window.location.assign(authorization_url);
    } catch (err) {
      setLoginInProgress(false);
      setLoginError(
        err instanceof Error ? err.message : "Could not start GitHub login",
      );
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.logout();
    } catch {
      // Even if the call fails (e.g. already expired), clear local state.
    } finally {
      if (mounted.current) {
        setUser(null);
        setStatus("unauthenticated");
      }
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      loginInProgress,
      loginError,
      loginWithGithub,
      logout,
      refreshUser,
    }),
    [user, status, loginInProgress, loginError, loginWithGithub, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Throws if used outside <AuthProvider>. */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error("useAuth must be used within an <AuthProvider>");
  }
  return ctx;
}

/** Convenience for the (unused but documented) direct-backend-root constant. */
export { BACKEND_ROOT };
