import type { ReactNode } from "react";
import "./globals.css";
import { Chrome } from "./chrome";

export const metadata = {
  title: "Panda",
  description: "Suivi d’actions + contacts",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <Chrome>{children}</Chrome>
      </body>
    </html>
  );
}
