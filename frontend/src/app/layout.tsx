import type { Metadata } from "next";

import { AuthProvider } from "@/context/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "SkillLedger",
  description: "Verified portfolios backed by GitHub contributions.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
