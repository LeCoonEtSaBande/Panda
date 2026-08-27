"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/", label: "Assistant" },
  { href: "/taches", label: "Tâches" },
  { href: "/courses", label: "Courses" },
  { href: "/libre", label: "Libre" },
];

export function Nav() {
  const path = usePathname();
  return (
    <nav className="nav">
      {ITEMS.map((it) => (
        <Link
          key={it.href}
          href={it.href}
          className={
            it.href === "/"
              ? path === "/"
                ? "is-active"
                : undefined
              : path === it.href || path.startsWith(`${it.href}/`)
                ? "is-active"
                : undefined
          }
        >
          {it.label}
        </Link>
      ))}
    </nav>
  );
}
