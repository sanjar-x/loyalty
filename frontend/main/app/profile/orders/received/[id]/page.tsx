import OrderDetailsClient from "../../[id]/OrderDetailsClient";

export const metadata = {
  title: "Заказ получен",
};

interface ReceivedOrderDetailsPageProps {
  params: Promise<{ id: string }>;
}

export default async function ReceivedOrderDetailsPage({ params }: ReceivedOrderDetailsPageProps) {
  const resolvedParams = await params;
  return <OrderDetailsClient id={resolvedParams?.id} variant="received" />;
}
