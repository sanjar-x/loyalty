import Link from 'next/link';

export default function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-6xl font-bold tracking-tight">404</h1>
      <p className="text-muted-foreground text-lg">Page not found</p>
      <Link href="/" className="text-primary hover:text-primary/80 underline underline-offset-4">
        Go home
      </Link>
    </main>
  );
}
