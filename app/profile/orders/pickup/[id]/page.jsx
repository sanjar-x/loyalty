import OrderDetailsClient from "../../[id]/OrderDetailsClient";

export const metadata = {
  title: "Заказ в пункте выдачи",
};

export default async function PickupOrderDetailsPage({ params }) {
  const resolvedParams = await params;
  return <OrderDetailsClient id={resolvedParams?.id} variant="pickup" />;
}
