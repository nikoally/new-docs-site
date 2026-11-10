import { source } from '@/lib/source';
import { createFromSource } from 'fumadocs-core/search/server';

// Prerender the search index at build time so the Worker just serves a static
// JSON file; searching happens client-side (RootProvider search type: 'static').
export const revalidate = false;

export const { staticGET: GET } = createFromSource(source, {
  language: 'english',
});
