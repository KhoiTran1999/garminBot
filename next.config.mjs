/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    proxyTimeout: 120000, // 120 giây (2 phút) cho AI gọi Tool Calling và phân tích dữ liệu Garmin
  },
  rewrites: async () => {
    return [
      {
        source: "/api/:path*",
        destination:
          process.env.NODE_ENV === "development"
            ? "http://127.0.0.1:8000/api/:path*"
            : "/api/index.py",
      },
    ];
  },
};

export default nextConfig;
