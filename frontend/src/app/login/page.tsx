"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { GithubLoginButton } from "@/components/auth/github-login-button";
import { useAuth } from "@/context/auth-context";
import { Spinner } from "@/components/ui/spinner";

function LoginContent() {
  const { status } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const oauthError = searchParams.get("error");

  // If already authenticated, send the user to the dashboard.
  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [status, router]);

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-8 px-6">
      <header className="space-y-2 text-center">
        <h1 className="text-3xl font-bold tracking-tight">Sign in to SkillLedger</h1>
        <p className="text-sm text-muted-foreground">
          Use your GitHub account to continue.
        </p>
      </header>

      <div className="w-full">
        <GithubLoginButton />
      </div>

      {oauthError ? (
        <p role="alert" className="text-sm text-red-600">
          {oauthError === "denied"
            ? "You cancelled the GitHub authorization. Try again when ready."
            : "Authentication failed. Please try again."}
        </p>
      ) : null}

      {status === "loading" ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Checking your session…
        </div>
      ) : null}

      <p className="text-xs text-muted-foreground">
        By continuing you agree to authenticate via GitHub OAuth. We only request
        read access to your profile and email.
      </p>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Spinner className="h-6 w-6" />
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
