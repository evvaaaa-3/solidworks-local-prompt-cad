"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Box, Boxes, Download, Gauge, History, Settings, Wrench } from "lucide-react";
import { api } from "@/lib/api";

const nav = [
  { href: "/", label: "Dashboard", icon: Gauge },
  { href: "/create", label: "Create Part", icon: Wrench },
  { href: "/history", label: "History", icon: History },
  { href: "/exports", label: "Exports", icon: Download },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [online, setOnline] = useState(false);
  useEffect(() => { api.health().then(() => setOnline(true)).catch(() => setOnline(false)); }, [pathname]);
  return (
    <div className="app-grid shell" style={{ display: "grid", gridTemplateColumns: "240px minmax(0,1fr)" }}>
      <aside className="sidebar" style={{ position: "sticky", top: 0, height: "100vh", borderRight: "1px solid var(--line)", background: "#0d1116", padding: 18 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 4px 24px" }}>
          <Box size={23} color="var(--accent)" /><div><strong>Prompt-to-CAD</strong><div className="muted" style={{ fontSize: 11 }}>SOLIDWORKS LOCAL</div></div>
        </div>
        <nav style={{ display: "grid", gap: 4 }}>
          {nav.map(({ href, label, icon: Icon }) => <Link key={href} href={href} style={{ display: "flex", gap: 10, alignItems: "center", padding: "10px 11px", borderRadius: 5, color: pathname === href ? "var(--text)" : "var(--muted)", background: pathname === href ? "#1a232c" : "transparent", textDecoration: "none", borderLeft: pathname === href ? "2px solid var(--accent)" : "2px solid transparent" }}><Icon size={17}/>{label}</Link>)}
          <div title="Future scope" style={{ display: "flex", gap: 10, alignItems: "center", padding: "10px 11px", color: "#56616c", marginTop: 8 }}><Boxes size={17}/>Assemblies <span style={{ fontSize: 10, marginLeft: "auto" }}>SOON</span></div>
        </nav>
        <div className="panel" style={{ position: "absolute", bottom: 18, left: 18, right: 18, padding: 12, display: "flex", alignItems: "center", gap: 9 }}>
          <span className={`status-dot ${online ? "online" : ""}`} /><div><div style={{ fontSize: 12, fontWeight: 700 }}>{online ? "Backend online" : "Backend offline"}</div><div className="muted" style={{ fontSize: 10 }}>127.0.0.1:8000</div></div>
        </div>
      </aside>
      <main style={{ minWidth: 0, padding: "28px clamp(18px,4vw,48px) 48px" }}>{children}</main>
    </div>
  );
}
