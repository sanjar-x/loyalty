import "server-only";

import crypto from "node:crypto";

function base64UrlEncode(buf) {
  return buf
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function base64UrlEncodeJson(value) {
  return base64UrlEncode(Buffer.from(JSON.stringify(value), "utf8"));
}

export function signHs256Jwt(payload, secret) {
  const header = { alg: "HS256", typ: "JWT" };
  const encodedHeader = base64UrlEncodeJson(header);
  const encodedPayload = base64UrlEncodeJson(payload);
  const data = `${encodedHeader}.${encodedPayload}`;
  const sig = crypto.createHmac("sha256", secret).update(data).digest();
  return `${data}.${base64UrlEncode(sig)}`;
}

export function parseTelegramInitData(initData) {
  const params = Object.fromEntries(new URLSearchParams(initData).entries());
  const userRaw = params.user;
  let user = null;
  if (typeof userRaw === "string") {
    try {
      user = JSON.parse(userRaw);
    } catch {
      user = null;
    }
  }

  const authDateRaw = params.auth_date;
  const authDate = typeof authDateRaw === "string" ? Number(authDateRaw) : null;

  return {
    params,
    user,
    authDate:
      typeof authDate === "number" && Number.isFinite(authDate)
        ? authDate
        : null,
  };
}

function parseTelegramInitDataPreservePlus(initData) {
  const params = {};

  const decode = (value) => {
    if (typeof value !== "string") return "";
    try {
      return decodeURIComponent(value);
    } catch {
      return value;
    }
  };

  const raw = typeof initData === "string" ? initData : "";
  const parts = raw.split("&");
  for (const part of parts) {
    if (!part) continue;
    const eq = part.indexOf("=");
    const rawKey = eq === -1 ? part : part.slice(0, eq);
    const rawValue = eq === -1 ? "" : part.slice(eq + 1);
    const key = decode(rawKey);
    const value = decode(rawValue);
    if (key) params[key] = value;
  }

  const userRaw = params.user;
  let user = null;
  if (typeof userRaw === "string") {
    try {
      user = JSON.parse(userRaw);
    } catch {
      user = null;
    }
  }

  const authDateRaw = params.auth_date;
  const authDate = typeof authDateRaw === "string" ? Number(authDateRaw) : null;

  return {
    params,
    user,
    authDate:
      typeof authDate === "number" && Number.isFinite(authDate)
        ? authDate
        : null,
  };
}

function buildTelegramDataCheckString(params) {
  const checkPairs = [];
  for (const [k, v] of Object.entries(params || {})) {
    if (k === "hash") continue;
    checkPairs.push([k, String(v)]);
  }
  checkPairs.sort(([a], [b]) => a.localeCompare(b));
  return checkPairs.map(([k, v]) => `${k}=${v}`).join("\n");
}

export function validateTelegramInitDataOrThrow({
  initData,
  botToken,
  maxAgeSeconds = 300,
}) {
  if (!initData || typeof initData !== "string") {
    throw new Error("Missing initData");
  }
  if (!botToken) {
    throw new Error("Missing bot token");
  }

  const normalizedBotToken =
    typeof botToken === "string" ? botToken.trim() : "";
  if (!normalizedBotToken) {
    throw new Error("Missing bot token");
  }

  const parsedA = parseTelegramInitData(initData);
  const parsedB = parseTelegramInitDataPreservePlus(initData);

  const candidates = [parsedA, parsedB];

  if (!parsedA?.params?.hash && !parsedB?.params?.hash) {
    throw new Error("Missing initData hash");
  }

  for (const candidate of candidates) {
    const hash = candidate?.params?.hash;
    if (!hash) continue;

    if (candidate.authDate) {
      const now = Math.floor(Date.now() / 1000);
      if (Math.abs(now - candidate.authDate) > maxAgeSeconds) {
        throw new Error("initData is too old");
      }
    }
  }

  // Telegram Mini Apps validation (core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)
  // secret_key = HMAC_SHA256(<bot_token>, key="WebAppData")
  const secretKey = crypto
    .createHmac("sha256", "WebAppData")
    .update(normalizedBotToken)
    .digest();

  // Defensive fallback: in case a client/server follows the reversed notation.
  // Still safe because it requires knowledge of the bot token.
  const secretKeyAlt = crypto
    .createHmac("sha256", normalizedBotToken)
    .update("WebAppData")
    .digest();

  const verifyCandidate = (candidate) => {
    const receivedRaw = candidate?.params?.hash;
    if (!receivedRaw) return false;

    const dataCheckString = buildTelegramDataCheckString(candidate.params);
    const expected1 = crypto
      .createHmac("sha256", secretKey)
      .update(dataCheckString)
      .digest("hex")
      .toLowerCase();
    const expected2 = crypto
      .createHmac("sha256", secretKeyAlt)
      .update(dataCheckString)
      .digest("hex")
      .toLowerCase();

    const received = String(receivedRaw).toLowerCase();
    const b = Buffer.from(received, "utf8");

    {
      const a = Buffer.from(expected1, "utf8");
      if (a.length === b.length && crypto.timingSafeEqual(a, b)) return true;
    }
    {
      const a = Buffer.from(expected2, "utf8");
      if (a.length === b.length && crypto.timingSafeEqual(a, b)) return true;
    }

    return false;
  };

  if (verifyCandidate(parsedA)) return parsedA;
  if (verifyCandidate(parsedB)) return parsedB;

  throw new Error("Invalid initData signature");
}

export function randomHandoffCode() {
  return base64UrlEncode(crypto.randomBytes(32));
}
