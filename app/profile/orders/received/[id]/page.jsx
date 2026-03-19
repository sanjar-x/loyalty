import OrderDetailsClient from "../../[id]/OrderDetailsClient";

export const metadata = {
  title: "Заказ получен",
};

export default async function ReceivedOrderDetailsPage({ params }) {
  const resolvedParams = await params;
  return <OrderDetailsClient id={resolvedParams?.id} variant="received" />;
}
