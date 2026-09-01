import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  agentRules: false,
  output: process.env.VERCEL ? undefined : "standalone",
};
export default nextConfig;
