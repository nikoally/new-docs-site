# SNE ITAC Docs (Fumadocs)

Documentation site for the Southern New England ITAC, built with [Fumadocs](https://fumadocs.dev) on Next.js and deployed to **Cloudflare Workers** with the [OpenNext Cloudflare adapter](https://opennext.js.org/cloudflare).

## Commands

| Command | What it does |
| --- | --- |
| `pnpm dev` | Next.js dev server at http://localhost:3000 |
| `pnpm build` | Plain `next build` (quick check that content compiles) |
| `pnpm preview` | Builds the Worker with OpenNext and runs it locally in `workerd` at http://localhost:8787 |
| `pnpm run deploy` | Builds and deploys to Cloudflare (run `pnpm wrangler login` once first). Note: plain `pnpm deploy` is a built-in pnpm command, so keep the `run`. |
| `pnpm upload` | Builds and uploads a new version without promoting it (for gradual rollouts) |
| `pnpm cf-typegen` | Generates `cloudflare-env.d.ts` after you add bindings to `wrangler.jsonc` |

The Worker name is `itac-docs` (see `wrangler.jsonc`). Every docs page, the search index, OG images, and the `llms.txt` routes are prerendered at build time, so the Worker mostly serves static assets and no R2/KV cache is configured.

## Content

- Pages live in `content/docs/**.mdx`; folder order and titles come from each folder's `meta.json`.
- `content/docs/training` is a sidebar **root** (it shows up in the section switcher at the top of the sidebar). Add more sections the same way, e.g. `content/docs/recommendations` with `"root": true`.
- Math: `$inline$` and `$$` blocks, rendered by KaTeX at build time. A literal dollar sign must be written `\$`.
- Frontmatter: `title`, `description`, `hideToc: true` (hides the right-hand table of contents).

Components you can use in MDX (defined in `components/mdx.tsx`, plus Fumadocs defaults):

```mdx
<Callout type="info|idea|warning|error|success" title="...">…</Callout>
<Example title="Optional title">…worked example…</Example>
<Accordions><Accordion title="Show answer">…</Accordion></Accordions>
<YouTube id="VIDEO_ID" start={535} />
<FloatImage src="/assets/…png" alt="…" width={350} align="right" />
```

## Migrating more of the Zensical site

`scripts/convert-zensical.py` converts one top-level nav section of the old `itac-docs` repo, using its `zensical.toml` nav for page order and folder titles:

```bash
pnpm convert Training        # = python3 scripts/convert-zensical.py ../itac-docs Training
```

It **overwrites** the matching `content/docs/<section>` folder. It translates admonitions (`!!!`/`???`), `\[ \]` math, currency `$`, MDX-unsafe `{ } <`, YouTube iframes, attr_list images, and `.md` links. Links to pages outside the converted section point at the live site (https://industrialassessment.com). Calculators and pages with custom JavaScript (Plotly/Chart.js) will need manual porting to React components.

## Deployment

Pushes to `main` deploy automatically through **Cloudflare Workers Builds** (Cloudflare's Git integration), configured on the `itac-docs` Worker in the Cloudflare dashboard. Pushes to other branches upload preview versions without touching production.

| Setting | Value |
| --- | --- |
| Repository | `nikoally/new-docs-site` |
| Production branch | `main` |
| Build command | `pnpm exec opennextjs-cloudflare build` |
| Deploy command | `pnpm exec opennextjs-cloudflare deploy` |
| Non-production branch deploy command | `pnpm exec opennextjs-cloudflare upload` |

Node and pnpm versions come from `.node-version` and the `packageManager` field in `package.json`.
