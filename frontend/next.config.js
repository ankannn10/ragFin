/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: { serverActions: true },

  async rewrites() {
    return [
      { source: '/api/:path*', destination: 'http://localhost:8000/:path*' },
      { source: '/rag/:path*', destination: 'http://localhost:8000/rag/:path*' },
    ];
  },
};
module.exports = nextConfig;
