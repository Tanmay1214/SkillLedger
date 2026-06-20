"use client";

import { forwardRef } from "react";

import { useAuth } from "@/context/auth-context";
import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/spinner";

/** Inline GitHub mark (no external icon dependency for a single glyph). */
function GithubIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={cn("h-5 w-5", className)}
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M12 .5C5.37.5 0 5.78 0 12.29c0 5.21 3.44 9.63 8.21 11.19.6.11.82-.25.82-.56 0-.28-.01-1.02-.02-2-3.34.71-4.04-1.58-4.04-1.58-.55-1.36-1.34-1.72-1.34-1.72-1.09-.73.08-.72.08-.72 1.21.08 1.85 1.22 1.85 1.22 1.07 1.79 2.81 1.27 3.5.97.11-.76.42-1.27.76-1.56-2.67-.3-5.47-1.3-5.47-5.79 0-1.28.47-2.33 1.23-3.15-.12-.3-.53-1.51.12-3.15 0 0 1-.31 3.3 1.2.96-.26 1.98-.39 3-.39s2.04.13 3 .39c2.29-1.51 3.3-1.2 3.3-1.2.65 1.64.24 2.85.12 3.15.77.82 1.23 1.87 1.23 3.15 0 4.5-2.81 5.48-5.49 5.77.43.36.81 1.08.81 2.18 0 1.58-.01 2.85-.01 3.24 0 .31.21.68.83.56C20.57 21.91 24 17.5 24 12.29 24 5.78 18.63.5 12 .5z" />
    </svg>
  );
}

export interface GithubLoginButtonProps {
  className?: string;
  label?: string;
}

/**
 * "Continue with GitHub" button.
 *
 * Triggers the OAuth flow by calling the backend `/auth/github/login`,
 * which returns the GitHub authorize URL; we then full-page redirect.
 * Shows a spinner + disables itself while the redirect is pending.
 */
export const GithubLoginButton = forwardRef<HTMLButtonElement, GithubLoginButtonProps>(
  function GithubLoginButton({ className, label = "Continue with GitHub" }, ref) {
    const { loginWithGithub, loginInProgress, loginError } = useAuth();

    return (
      <div className="flex flex-col items-center gap-2">
        <button
          ref={ref}
          type="button"
          onClick={() => void loginWithGithub()}
          disabled={loginInProgress}
          className={cn(
            "inline-flex h-12 w-full items-center justify-center gap-3 rounded-md bg-[#24292f] px-6 text-base font-medium text-white transition-colors",
            "hover:bg-[#24292f]/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#24292f]",
            "disabled:cursor-not-allowed disabled:opacity-70",
            className,
          )}
        >
          {loginInProgress ? <Spinner className="text-white" /> : <GithubIcon />}
          <span>{loginInProgress ? "Redirecting to GitHub…" : label}</span>
        </button>
        {loginError ? (
          <p role="alert" className="text-sm text-red-600">
            {loginError}
          </p>
        ) : null}
      </div>
    );
  },
);
