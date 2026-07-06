"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Box, Download, FlaskConical, History, Plus, Server } from "lucide-react";
import { api, OutputFile } from "@/lib/api";
import { FileTable } from "@/components/FileTable";

const tools = ["Cube", "Block", "Cylinder", "Disc", "Plate", "Tube", "Plate + Hole", "Cone", "Sphere", "Torus"];
const actions = [
  { href: "/create", label: "New Part", detail: "Compose a deterministic CAD request", icon: Plus },
  { href: "/create", label: "Dry Run", detail: "Validate without opening SolidWorks", icon: FlaskConical },
  { href: "/history", label: "View History", detail: "Inspect generated local parts", icon: History },
  { href: "/exports", label: "Export STEP", detail: "Review and download exports", icon: Download },
];

export default function Dashboard() {
  const [files, setFiles] = useState<OutputFile[]>([]);
  const [online, setOnline] = useState<boolean | null>(null);
  useEffect(() => { api.health().then(() => setOnline(true)).catch(() => setOnline(false)); api.outputs().then(setFiles).catch(() => setFiles([])); }, []);
  return <div style={{ maxWidth: 1180, margin: "0 auto" }}>
    <header style={{ display: "flex", justifyContent: "space-between", gap: 20, alignItems: "flex-start", marginBottom: 28 }}><div><div className="eyebrow">Local CAD workspace</div><h1 style={{ fontSize: 32, margin: "6px 0 8px" }}>Engineering control console</h1><p className="muted" style={{ margin: 0, maxWidth: 620 }}>Parse, validate, and execute deterministic SolidWorks part operations without sending project data to the cloud.</p></div><div className="panel" style={{ padding: "10px 13px", display: "flex", gap: 9, alignItems: "center" }}><Server size={16}/><span className={`status-dot ${online ? "online" : ""}`}/><span style={{ fontSize: 12 }}>{online === null ? "Checking API" : online ? "API operational" : "API unavailable"}</span></div></header>
    <section style={{ marginBottom: 26 }}><div className="eyebrow" style={{ marginBottom: 10 }}>Supported primitives</div><div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>{tools.map(tool => <span key={tool} style={{ border: "1px solid var(--line)", background: "#10161c", borderRadius: 4, padding: "6px 9px", fontSize: 12 }}>{tool}</span>)}</div></section>
    <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: 12, marginBottom: 30 }}>{actions.map(({ href, label, detail, icon: Icon }) => <Link className="panel" key={label} href={href} style={{ padding: 17, textDecoration: "none", color: "inherit", minHeight: 120 }}><Icon size={20} color="var(--accent)"/><h2 style={{ fontSize: 16, margin: "18px 0 5px" }}>{label}</h2><p className="muted" style={{ fontSize: 12, margin: 0 }}>{detail}</p></Link>)}</section>
    <section><div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}><div><div className="eyebrow">Output registry</div><h2 style={{ margin: "4px 0 0", fontSize: 20 }}>Recent generated files</h2></div><Box size={20} color="var(--muted)"/></div><FileTable files={files.slice(0, 7)}/></section>
  </div>;
}
