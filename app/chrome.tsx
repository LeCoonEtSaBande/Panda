"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const ITEMS = [
  { href: "/", label: "Assistant" },
  { href: "/taches", label: "Tâches" },
  { href: "/courses", label: "Courses" },
  { href: "/libre", label: "Libre" },
];

function Nav() {
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

export function Chrome({ children }: { children: ReactNode }) {
  const path = usePathname();
  const hide = path === "/login";
  return (
    <div className="shell">
      {hide ? null : (
        <header className="top">
          <a className="brand" href="/parametres">
            Panda
          </a>
          <a className="only-pc muted" href="/contacts">
            Carnet
          </a>
        </header>
      )}
      <div className="page">{children}</div>
      {hide ? null : <Nav />}
    </div>
  );
}
