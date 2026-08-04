import type { NextConfig } from "next";

const backendHostport = process.env.BACKEND_HOSTPORT?.trim();

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1"],
  devIndicators: false,
  async rewrites() {
    if (!backendHostport) return [];
    return [
      {
        source: "/api/:path*",
        destination: `http://${backendHostport}/:path*`,
      },
    ];
  },
};

export default nextConfig;
