import type { Contact } from "@/lib/types";

export function canCreateContact(c: {
  lastName?: string;
  firstName?: string;
  organization?: string;
  phone?: string;
  email?: string;
  url?: string;
}): boolean {
  const identity = Boolean(
    c.lastName?.trim() || c.firstName?.trim() || c.organization?.trim(),
  );
  const coord = Boolean(c.phone?.trim() || c.email?.trim() || c.url?.trim());
  return identity && coord;
}

export function autoPronom(
  organization: string,
  orgs: string[],
  chosen?: "tu" | "vous",
): "tu" | "vous" {
  if (chosen === "tu") return "tu";
  const hit = orgs.some(
    (o) => o.trim().toLowerCase() === organization.trim().toLowerCase(),
  );
  return hit ? "tu" : (chosen ?? "vous");
}

export function contactLabel(c: Pick<Contact, "firstName" | "lastName" | "organization">) {
  return [c.firstName, c.lastName, c.organization].filter(Boolean).join(" ");
}

export function sameOrgAsUser(organization: string, orgs: string[]): boolean {
  return orgs.some(
    (o) => o.trim().toLowerCase() === organization.trim().toLowerCase(),
  );
}
