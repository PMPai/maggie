/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      { source: '/api/:path*', destination: 'http://api:8000/api/:path*' },
      { source: '/health', destination: 'http://api:8000/health' },
    ];
  },
};
export default nextConfig;
