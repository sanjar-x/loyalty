import OrderDetailsClient from "../../[id]/OrderDetailsClient";

export const metadata = {
  title: "Заказ в пути",
};

interface InTransitOrderDetailsPageProps {
  params: Promise<{ id: string }>;
}

export default async function InTransitOrderDetailsPage({ params }: InTransitOrderDetailsPageProps) {
  const resolvedParams = await params;
  return <OrderDetailsClient id={resolvedParams?.id} variant="inTransit" />;
}
