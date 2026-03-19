import OrderDetailsClient from "./OrderDetailsClient";

export const metadata = {
  title: "Заказ",
};

export default async function OrderDetailsPage({ params }) {
  const resolvedParams = await params;
  return <OrderDetailsClient id={resolvedParams?.id} />;
}
