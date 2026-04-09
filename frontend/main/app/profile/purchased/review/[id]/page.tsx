import ReviewClient from "./ReviewClient";

export const metadata = {
  title: "Оцените товар",
};

interface ReviewPageProps {
  params: Promise<{ id: string }>;
}

export default async function ReviewPage({ params }: ReviewPageProps) {
  const resolvedParams = await params;
  return <ReviewClient id={resolvedParams?.id} />;
}
