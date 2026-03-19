import ReviewClient from "./ReviewClient";

export const metadata = {
  title: "Оцените товар",
};

export default async function ReviewPage({ params }) {
  // Next.js (newer versions) may provide `params` as a Promise.
  // `await` is safe for both promise and non-promise values.
  const resolvedParams = await params;
  return <ReviewClient id={resolvedParams?.id} />;
}
