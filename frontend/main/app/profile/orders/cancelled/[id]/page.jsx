import OrderDetailsClient from "../../[id]/OrderDetailsClient";

export const metadata = {
  title: "Заказ отменён",
};

export default async function CancelledOrderDetailsPage({ params }) {
  const resolvedParams = await params;
  return <OrderDetailsClient id={resolvedParams?.id} variant="cancelled" />;
}
