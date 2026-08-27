import type { ReactNode } from "react";
import "./globals.css";
import { Gauge } from "./gauge";
import { Nav } from "./nav";

export const metadata = {
  title: "Panda",
  description: "Suivi d’actions + contacts",
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
            <Gauge />
          </header>
          {children}
          <Nav />
        </div>
      </body>
    </html>
  );
}
