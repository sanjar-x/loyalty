import OrderDetailsClient from "../../[id]/OrderDetailsClient";

export const metadata = {
  title: "Заказ отменён",
};

interface CancelledOrderDetailsPageProps {
  params: Promise<{ id: string }>;
}

export default async function CancelledOrderDetailsPage({ params }: CancelledOrderDetailsPageProps) {
  const resolvedParams = await params;
  return <OrderDetailsClient id={resolvedParams?.id} variant="cancelled" />;
}
