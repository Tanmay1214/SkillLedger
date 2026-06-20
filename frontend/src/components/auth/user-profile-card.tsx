"use client";

import { ExternalLink, LogOut } from "lucide-react";

import { useAuth } from "@/context/auth-context";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface UserProfileCardProps {
  className?: string;
  /** Called after a successful logout (e.g. to redirect to /login). */
  onLogout?: () => void;
}

/**
 * Displays the signed-in user's GitHub identity with avatar, username,
 * a profile link, and a logout action.
 */
export function UserProfileCard({ className, onLogout }: UserProfileCardProps) {
  const { user, logout } = useAuth();

  if (!user) return null;

  const handleLogout = async () => {
    await logout();
    onLogout?.();
  };

  return (
    <div
      className={cn(
        "flex w-full max-w-md flex-col items-center gap-4 rounded-lg border border-border bg-background p-6 text-center shadow-sm",
        className,
      )}
    >
      <img
        src={user.avatar_url ?? undefined}
        alt={`${user.username}'s avatar`}
        width={96}
        height={96}
        className="h-24 w-24 rounded-full border border-border object-cover"
      />

      <div className="space-y-1">
        <h2 className="text-xl font-semibold">
          {user.name ?? user.username}
        </h2>
        <p className="text-sm text-muted-foreground">@{user.username}</p>
        {user.email ? (
          <p className="text-sm text-muted-foreground">{user.email}</p>
        ) : null}
      </div>

      {user.profile_url ? (
        <a
          href={user.profile_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          View GitHub profile <ExternalLink className="h-3.5 w-3.5" />
        </a>
      ) : null}

      <Button variant="outline" className="mt-2 w-full" onClick={() => void handleLogout()}>
        <LogOut className="h-4 w-4" />
        Log out
      </Button>
    </div>
  );
}
