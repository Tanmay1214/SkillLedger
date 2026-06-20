"use client";

import type { Route } from "next";
import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/context/auth-context";
import { Spinner } from "@/components/ui/spinner";

export interface ProtectedRouteProps {
  children: ReactNode;
  /** Where to send unauthenticated users. Defaults to /login. */
  redirectTo?: Route;
}

/**
 * Client-side route guard.
 *
 * While the session is still being resolved we show a loading state instead
 * of flashing protected content. Once resolved, an unauthenticated user is
 * redirected to /login. (Server-side `middleware.ts` is the primary guard;
 * this is the in-app belt-and-suspenders.)
 */
export function ProtectedRoute({ children, redirectTo = "/login" }: ProtectedRouteProps) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(redirectTo);
    }
  }, [status, router, redirectTo]);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    // Redirect kicked off in effect; render nothing meanwhile.
    return null;
  }

  return <>{children}</>;
}
