import { Suspense } from "react";
import AssistantPage from "./assistant-client";

export default function Page() {
  return (
    <Suspense fallback={<main className="muted">…</main>}>
      <AssistantPage />
    </Suspense>
  );
}
