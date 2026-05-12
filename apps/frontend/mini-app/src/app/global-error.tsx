'use client';

export default function GlobalError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
        <h1 className="text-4xl font-bold tracking-tight">Something went wrong</h1>
        <p className="text-lg text-gray-600">{error.message}</p>
        <button
          onClick={() => unstable_retry()}
          className="rounded-md bg-black px-4 py-2 text-white transition-colors hover:bg-gray-800"
        >
          Try again
        </button>
      </body>
    </html>
  );
}
