"use client";

import { ErrorState } from "@/components/error-state";

export default function GlobalError({ reset }: { reset: () => void }) {
  return (
    <main className="fatal-state">
      <ErrorState message="The interface could not be loaded." actionLabel="Try again" onAction={reset} />
    </main>
  );
}
