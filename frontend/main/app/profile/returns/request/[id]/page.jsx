"use client";

import { use } from "react";

import ReturnRequestClient from "./ReturnRequestClient";

export default function ReturnRequestPage({ params }) {
  const { id } = use(params);
  return <ReturnRequestClient id={id} />;
}
