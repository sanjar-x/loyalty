'use client';

export default function Error({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-4xl font-bold tracking-tight">Something went wrong</h1>
      <p className="text-muted-foreground text-lg">{error.message}</p>
      <button
        onClick={() => unstable_retry()}
        className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-md px-4 py-2 transition-colors"
      >
        Try again
      </button>
    </main>
  );
}
