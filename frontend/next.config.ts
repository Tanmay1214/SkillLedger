import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The backend sets its own cookies; nothing special needed here because
  // we call the backend same-site via a top-level redirect for login.
  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;
