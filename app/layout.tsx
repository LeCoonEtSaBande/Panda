import type { ReactNode } from "react";
import "./globals.css";
import { Gauge } from "./gauge";
import { Nav } from "./nav";

export const metadata = {
  title: "Panda",
  description: "Suivi d’actions + contacts",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <div className="shell">
          <header className="top">
            <a className="brand" href="/parametres">
              Panda
            </a>
            <a className="only-pc muted" href="/contacts">
              Carnet
            </a>
            <Gauge />
          </header>
          <div className="page">{children}</div>
          <Nav />
        </div>
      </body>
    </html>
  );
}
