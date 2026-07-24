"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Graph } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { fetchStatus } from "@/lib/api";
import type { StatusResponse } from "@/lib/types";

const NAVIGATION = [
  { href: "/single", label: "Single Molecule" },
  { href: "/batch", label: "Batch Screening" },
  { href: "/about", label: "Model Information" },
] as const;

export function AppHeader() {
  const pathname = usePathname();
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let active = true;
    fetchStatus().then((value) => {
      if (active) { setStatus(value); setUnavailable(false); }
    }).catch(() => {
      if (active) { setStatus(null); setUnavailable(true); }
    });
    return () => { active = false; };
  }, []);

  return (
    <header className="global-header">
      <Link className="product-lockup" href="/single" aria-label="ADME Discovery Workspace home">
        <Graph size={30} weight="duotone" aria-hidden="true" />
        <span>ADME Discovery Workspace</span>
      </Link>
      <nav className="main-navigation" aria-label="Primary navigation">
        {NAVIGATION.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined}>{item.label}</Link>;
        })}
      </nav>
      <div className="header-status" aria-live="polite">
        <span className={`status-pill ${unavailable ? "is-error" : status ? "is-ok" : "is-muted"}`}><i aria-hidden="true" />{unavailable ? "Backend Unavailable" : status ? "Backend Connected" : "Checking Backend"}</span>
        <span className={`status-pill ${status?.prediction_mode === "mock" ? "is-warning" : status ? "is-ok" : "is-muted"}`}><i aria-hidden="true" />{status?.prediction_mode === "mock" ? "Mock Predictions" : status ? "Real ADMET-AI" : "Mode Unknown"}</span>
      </div>
    </header>
  );
}
