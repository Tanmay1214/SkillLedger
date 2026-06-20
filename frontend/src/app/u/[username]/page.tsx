import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { apiClient } from "@/lib/api-client";
import type { PortfolioResponse } from "@/types/portfolio";
import PortfolioView from "@/components/portfolio/PortfolioView";

interface Props {
  params: Promise<{ username: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { username } = await params;
  return {
    title: `${username} — ProofForge Portfolio`,
    description: `Verified developer portfolio for ${username}, powered by ProofForge.`,
  };
}

export default async function PortfolioPage({ params }: Props) {
  const { username } = await params;

  let portfolio: PortfolioResponse;
  try {
    portfolio = await apiClient.getPortfolio(username);
  } catch {
    notFound();
  }

  return <PortfolioView portfolio={portfolio} />;
}
