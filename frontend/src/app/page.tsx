"use client";

import Link from "next/link";

import { useAuth } from "@/context/auth-context";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function HomePage() {
  const { status } = useAuth();

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="space-y-3">
        <h1 className="text-4xl font-bold tracking-tight">SkillLedger</h1>
        <p className="text-muted-foreground">
          Verified portfolios, backed by your real GitHub contributions.
        </p>
      </div>
      <Link
        href={status === "authenticated" ? "/dashboard" : "/login"}
        className={cn(buttonVariants())}
      >
        {status === "authenticated" ? "Go to dashboard" : "Sign in"}
      </Link>
    </main>
  );
}
