import { createMDX } from 'fumadocs-mdx/next';
import { initOpenNextCloudflareForDev } from '@opennextjs/cloudflare';

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const config = {
  reactStrictMode: true,
  images: {
    // No image optimization service on Workers by default; images are served as-is.
    unoptimized: true,
  },
};

export default withMDX(config);

// Exposes Cloudflare bindings (getCloudflareContext) during `next dev`.
initOpenNextCloudflareForDev();
