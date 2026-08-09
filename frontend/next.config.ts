import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backendUrl = (process.env.BACKEND_URL ?? "https://leap-api-tdy5.onrender.com").replace(/\/$/, "");
    return backendUrl
      ? [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }]
      : [];
  },
};

export default nextConfig;
