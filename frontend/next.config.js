/** @type {import('next').NextConfig} */
const serverApiUrl = process.env.NEXT_SERVER_API_URL;

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (!serverApiUrl) {
      return [];
    }
    return [
      {
        source: '/api/:path*',
        destination: `${serverApiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
