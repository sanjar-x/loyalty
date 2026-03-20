import ReturnRequestClient from "./ReturnRequestClient";

export const metadata = {
  title: "Заявка на возврат",
};

interface ReturnRequestPageProps {
  params: Promise<{ id: string }>;
}

export default async function ReturnRequestPage({ params }: ReturnRequestPageProps) {
  const resolvedParams = await params;
  return <ReturnRequestClient id={resolvedParams?.id} />;
}
