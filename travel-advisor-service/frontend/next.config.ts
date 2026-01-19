import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // reactCompiler temporarily disabled to investigate source map warnings in dev
  // reactCompiler: true,
  
  // Suppress hydration warnings caused by browser extensions (Bitdefender, etc.)
  reactStrictMode: true,
  
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
      {
        protocol: 'https',
        hostname: 'res.cloudinary.com',
      },
      {
        protocol: 'https',
        hostname: 'upload.wikimedia.org',
      },
      {
        protocol: 'https',
        hostname: 'picsum.photos',
      },
      {
        protocol: 'https',
        hostname: 'placehold.co',
      },
      {
        protocol: 'https',
        hostname: 'source.unsplash.com',
      },
      {
        protocol: 'https',
        hostname: 'i.vntrip.vn',
      },
      {
        protocol: 'https',
        hostname: 'statics.vntrip.vn',
      },
      {
        protocol: 'https',
        hostname: 'media.gody.vn',
      },
      {
        protocol: 'https',
        hostname: 'media2.gody.vn',
      },
      {
        protocol: 'https',
        hostname: 'h3jd9zjnmsobj.vcdn.cloud',
      },
      {
        protocol: 'https',
        hostname: 'vcdn.cloud',
      },
    ],
  },
};

export default nextConfig;
