import Link from 'next/link';

const modules = [
  { href: '/docs/training/basics', title: 'Power and Energy Fundamentals' },
  { href: '/docs/training/engineering-economics', title: 'Engineering Economics' },
  { href: '/docs/training/technical-writing', title: 'Technical Writing' },
  { href: '/docs/training/electric-motor-systems', title: 'Electric Motor Systems' },
  { href: '/docs/training/compressed-air', title: 'Compressed Air' },
];

export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-center px-4 py-16">
      <p className="mb-2 text-sm font-medium text-fd-muted-foreground">
        Southern New England Industrial Training and Assessment Center
      </p>
      <h1 className="mb-4 text-4xl font-bold tracking-tight">ITAC Documentation</h1>
      <p className="mb-10 max-w-2xl text-lg text-fd-muted-foreground">
        Training modules for energy assessment work: the electrical, economic, and writing fundamentals behind
        every recommendation.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {modules.map((m, i) => (
          <Link
            key={m.href}
            href={m.href}
            className="rounded-xl border bg-fd-card p-4 transition-colors hover:bg-fd-accent"
          >
            <p className="text-xs font-medium text-fd-muted-foreground">Module {i + 1}</p>
            <p className="font-medium">{m.title}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}
