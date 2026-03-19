import ReturnRequestClient from "./ReturnRequestClient";

export const metadata = {
  title: "Заявка на возврат",
};

export default async function ReturnRequestPage({ params }) {
  const resolvedParams = await params;
  return <ReturnRequestClient id={resolvedParams?.id} />;
}
