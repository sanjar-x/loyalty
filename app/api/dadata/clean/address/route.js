import { NextResponse } from "next/server";

export async function POST(req) {
  const token = process.env.DADATA_TOKEN;
  const secret = process.env.DADATA_SECRET;
  if (!token) {
    return NextResponse.json(
      { error: "Missing server env DADATA_TOKEN" },
      { status: 500 },
    );
  }
  if (!secret) {
    return NextResponse.json(
      {
        error: "Missing server env DADATA_SECRET",
        hint: "DaData Cleaner API requires X-Secret header",
      },
      { status: 500 },
    );
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const query = body?.query;
  if (typeof query !== "string") {
    return NextResponse.json(
      { error: "query must be a string" },
      { status: 400 },
    );
  }

  const q = query.trim();
  if (!q) {
    return NextResponse.json({ items: [] });
  }

  const upstream = await fetch(
    "https://cleaner.dadata.ru/api/v1/clean/address",
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: `Token ${token}`,
        "X-Secret": secret,
      },
      body: JSON.stringify([q]),
    },
  );

  const text = await upstream.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    // ignore
  }

  if (!upstream.ok) {
    return NextResponse.json(
      {
        error: "DaData request failed",
        status: upstream.status,
        details: json ?? text,
      },
      { status: 502 },
    );
  }

  return NextResponse.json({ items: Array.isArray(json) ? json : [] });
}
