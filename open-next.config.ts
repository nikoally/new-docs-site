import { defineCloudflareConfig } from '@opennextjs/cloudflare';

// Docs pages are fully prerendered at build time, so no incremental cache
// (R2/KV) is needed. Add one here if you later introduce ISR / revalidation:
// https://opennext.js.org/cloudflare/caching
export default defineCloudflareConfig({});
