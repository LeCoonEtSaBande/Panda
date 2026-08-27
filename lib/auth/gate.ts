const COOKIE = "panda_gate";
export const GATE_COOKIE = COOKIE;
const DAYS = 60;

function encoder() {
  return new TextEncoder();
}

async function hmacHex(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder().encode(message));
  return [...new Uint8Array(sig)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i += 1) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

export function gateConfigured(): boolean {
  return Boolean(
    process.env.PANDA_USER?.trim() && process.env.PANDA_PASSWORD,
  );
}

export function credentialsOk(user: string, password: string): boolean {
  const expectUser = process.env.PANDA_USER?.trim() ?? "";
  const expectPass = process.env.PANDA_PASSWORD ?? "";
  if (!expectUser || !expectPass) return false;
  return (
    safeEqual(user.trim(), expectUser) && safeEqual(password, expectPass)
  );
}

export async function makeGateToken(): Promise<string | null> {
  const secret = process.env.PANDA_PASSWORD;
  if (!secret) return null;
  const exp = Date.now() + DAYS * 24 * 60 * 60 * 1000;
  const body = `v1.${exp}`;
  const sig = await hmacHex(secret, body);
  return `${body}.${sig}`;
}

export async function gateTokenOk(token: string | undefined): Promise<boolean> {
  if (!token || !gateConfigured()) return false;
  const secret = process.env.PANDA_PASSWORD ?? "";
  const cut = token.lastIndexOf(".");
  if (cut < 0) return false;
  const body = token.slice(0, cut);
  const sig = token.slice(cut + 1);
  const [ver, expRaw] = body.split(".");
  if (ver !== "v1") return false;
  const exp = Number(expRaw);
  if (!Number.isFinite(exp) || Date.now() > exp) return false;
  const expect = await hmacHex(secret, body);
  return safeEqual(sig, expect);
}

export function gateCookieHeader(token: string): string {
  const maxAge = DAYS * 24 * 60 * 60;
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `${COOKIE}=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${secure}`;
}

export function clearGateCookieHeader(): string {
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `${COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${secure}`;
}

export function readGateCookie(
  cookies: { name: string; value: string }[],
): string | undefined {
  return cookies.find((c) => c.name === COOKIE)?.value;
}
