import OrderDetailsClient from "../../[id]/OrderDetailsClient";

export const metadata = {
  title: "Заказ в пути",
};

export default async function InTransitOrderDetailsPage({ params }) {
  const resolvedParams = await params;
  return <OrderDetailsClient id={resolvedParams?.id} variant="inTransit" />;
}
