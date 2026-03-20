import OrderDetailsClient from "./OrderDetailsClient";

export const metadata = {
  title: "Заказ",
};

interface OrderDetailsPageProps {
  params: Promise<{ id: string }>;
}

export default async function OrderDetailsPage({ params }: OrderDetailsPageProps) {
  const resolvedParams = await params;
  return <OrderDetailsClient id={resolvedParams?.id} />;
}
