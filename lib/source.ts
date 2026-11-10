import { llms, loader } from 'fumadocs-core/source';
import { lucideIconsPlugin } from 'fumadocs-core/source/lucide-icons';
import { docsRoute } from './shared';
import { defineDocs } from 'fumadocs-mdx/macro';
import { applyMdxPreset } from 'fumadocs-mdx/config';
import { metaSchema, pageSchema } from 'fumadocs-core/source/schema';
import { z } from 'zod';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

const docs = defineDocs({
  dir: 'content/docs',
  docs: {
    schema: pageSchema.extend({
      /** hide the right-hand table of contents (Zensical's `hide: [toc]`) */
      hideToc: z.boolean().default(false),
    }),
    // LaTeX math ($...$ and $$ blocks) rendered with KaTeX at build time.
    // rehype-katex must run before syntax highlighting.
    mdxOptions: applyMdxPreset({
      remarkPlugins: [remarkMath],
      rehypePlugins: (v) => [rehypeKatex, ...v],
    }),
    postprocess: {
      includeProcessedMarkdown: true,
    },
  },
  meta: {
    schema: metaSchema,
  },
});

// See https://fumadocs.dev/docs/headless/source-api for more info
export const source = loader({
  baseUrl: docsRoute,
  source: docs.toFumadocsSource(),
  plugins: [lucideIconsPlugin()],
});

export const docsLlms = llms(source, {
  renderPage: async (page) => `# ${page.data.title} (${page.url})

${await page.data.getText('processed')}`,
});
