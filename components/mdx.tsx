import defaultMdxComponents from 'fumadocs-ui/mdx';
import { Accordion, Accordions } from 'fumadocs-ui/components/accordion';
import { Callout } from 'fumadocs-ui/components/callout';
import { Calculator } from 'lucide-react';
import type { MDXComponents } from 'mdx/types';
import type { CSSProperties, ReactNode } from 'react';
import { cn } from '@/lib/cn';

/** Worked example — replaces Zensical's `!!! example` admonition. */
function Example({ title = 'Example', children }: { title?: string; children: ReactNode }) {
  return (
    <Callout
      title={title}
      icon={<Calculator className="size-5 -me-0.5 text-(--callout-color)" />}
      style={{ '--callout-color': 'var(--color-fd-primary)' } as CSSProperties}
    >
      {children}
    </Callout>
  );
}

/** Responsive, privacy-enhanced YouTube embed. */
function YouTube({ id, start, title = 'YouTube video player' }: { id: string; start?: number; title?: string }) {
  const src = `https://www.youtube-nocookie.com/embed/${id}${start ? `?start=${start}` : ''}`;
  return (
    <iframe
      src={src}
      title={title}
      className="my-6 aspect-video w-full rounded-xl border"
      loading="lazy"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
      referrerPolicy="strict-origin-when-cross-origin"
      allowFullScreen
    />
  );
}

/** Image with optional width / float — replaces `![](..){width=.. align=..}`. */
function FloatImage({
  src,
  alt,
  width,
  align,
}: {
  src: string;
  alt: string;
  width?: number;
  align?: 'left' | 'right' | 'center';
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      loading="lazy"
      style={width ? { width, maxWidth: '100%' } : undefined}
      className={cn(
        'rounded-lg',
        align === 'right' && 'sm:float-right sm:ml-6 sm:mb-4',
        align === 'left' && 'sm:float-left sm:mr-6 sm:mb-4',
        align === 'center' && 'mx-auto',
      )}
    />
  );
}

export function getMDXComponents(components?: MDXComponents) {
  return {
    ...defaultMdxComponents,
    Accordion,
    Accordions,
    Example,
    YouTube,
    FloatImage,
    ...components,
  } satisfies MDXComponents;
}

export const useMDXComponents = getMDXComponents;

declare global {
  type MDXProvidedComponents = ReturnType<typeof getMDXComponents>;
}
