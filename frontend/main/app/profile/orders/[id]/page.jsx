"use client";

import { use } from "react";

import OrderDetailsClient from "./OrderDetailsClient";

export default function OrderDetailsPage({ params }) {
  const { id } = use(params);
  return <OrderDetailsClient id={id} />;
}
