import { redirect } from "next/navigation";

export default function PickupSearchRedirectPage() {
  redirect("/checkout/pickup?step=search");
}
