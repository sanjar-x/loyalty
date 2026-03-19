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
    return NextResponse.json({ suggestions: [] });
  }

  const countRaw = body?.count;
  const count =
    typeof countRaw === "number" && Number.isFinite(countRaw)
      ? Math.min(10, Math.max(1, Math.floor(countRaw)))
      : 5;

  const headers = {
    Accept: "application/json",
    "Content-Type": "application/json",
    Authorization: `Token ${token}`,
  };

  // If project security requires it, DaData accepts X-Secret too.
  if (secret) headers["X-Secret"] = secret;

  const upstream = await fetch(
    "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address",
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        query: q,
        count,
        from_bound: { value: "city" },
        to_bound: { value: "settlement" },
      }),
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

  return NextResponse.json(
    json && typeof json === "object" ? json : { suggestions: [] },
  );
}
