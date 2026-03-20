import OrderDetailsClient from "../../[id]/OrderDetailsClient";

export const metadata = {
  title: "Заказ в пункте выдачи",
};

interface PickupOrderDetailsPageProps {
  params: Promise<{ id: string }>;
}

export default async function PickupOrderDetailsPage({ params }: PickupOrderDetailsPageProps) {
  const resolvedParams = await params;
  return <OrderDetailsClient id={resolvedParams?.id} variant="pickup" />;
}
