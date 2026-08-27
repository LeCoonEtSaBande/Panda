import { createClient } from "@supabase/supabase-js";

const OWNER_EMAIL = "panda-owner@example.com";

function admin() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;
  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

export async function ensureOwnerUser(password: string): Promise<void> {
  const sb = admin();
  if (!sb) return;

  const created = await sb.auth.admin.createUser({
    email: OWNER_EMAIL,
    password,
    email_confirm: true,
  });

  if (!created.error) return;

  const listed = await sb.auth.admin.listUsers({ page: 1, perPage: 200 });
  const existing = listed.data.users.find(
    (u) => u.email?.toLowerCase() === OWNER_EMAIL,
  );
  if (existing) {
    await sb.auth.admin.updateUserById(existing.id, { password });
  }
}

export function ownerEmail() {
  return OWNER_EMAIL;
}
