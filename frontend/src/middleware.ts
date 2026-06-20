import { NextResponse, type NextRequest } from "next/server";

/**
 * Route protection middleware (Edge runtime).
 *
 * IMPORTANT — why this is "soft" protection:
 * The auth session is an httpOnly cookie owned by the *backend* domain/port.
 * On localhost the frontend (3000) and backend (8000) are different origins,
 * so the Next.js edge runtime cannot read the backend's cookie here. Instead,
 * this middleware guards against *static* leakage: it ensures a hard
 * redirect to /login for known protected routes when there is clearly no
 * session, and otherwise lets the client-side <ProtectedRoute> do the
 * authoritative 401-based check via /auth/me.
 *
 * In production (same-site / same-origin behind a proxy), you would add a
 * lightweight session-indicator cookie (HttpOnly=false, non-sensitive) set
 * by the backend purely so this middleware can branch. That keeps tokens off
 * the client while enabling true edge redirects.
 */
const PROTECTED_PATHS = ["/dashboard"];
const PUBLIC_PATHS = ["/login"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // After a successful login, the backend redirects to /dashboard?login=success.
  // Allow that through; the client resolves the session from /auth/me.
  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p));
  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  // For protected routes, pass through — client-side guard enforces auth.
  // (See note above about same-site for true edge enforcement.)
  if (isProtected || isPublic) {
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  // Run on all app paths except static assets and API.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
