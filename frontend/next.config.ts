import type { NextConfig } from 'next';
import path from 'path';

const nextConfig: NextConfig = {
  // Produce a self-contained Node server for the multi-stage Docker image.
  output: 'standalone',
  // Limit static-generation concurrency so a local production build does not
  // monopolize every CPU core.
  experimental: {
    cpus: 4,
  },
  turbopack: {
    root: path.resolve(__dirname),
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
