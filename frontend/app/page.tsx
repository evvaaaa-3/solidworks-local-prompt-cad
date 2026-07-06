"use client";

import { useEffect, useState } from "react";
import { Box, Braces, CheckCircle2, CircleAlert, LoaderCircle, Play, ScanSearch } from "lucide-react";
import { api, ExecuteResponse, ParseResponse } from "@/lib/api";

const templates = [
  { label: "Cube", prompt: "create a 50 mm cube" },
  { label: "Plate with Hole", prompt: "create plate 100 by 60 by 5 mm with hole diameter 20 mm" },
  { label: "Cone", prompt: "create cone base diameter 50 mm height 80 mm" },
  { label: "Sphere", prompt: "create sphere diameter 50 mm" },
];

export default function PromptToCadPage() {
  const [prompt, setPrompt] = useState("create sphere diameter 50 mm");
  const [online, setOnline] = useState<boolean | null>(null);
  const [loading, setLoading] = useState<"parse" | "execute" | null>(null);
  const [response, setResponse] = useState<ParseResponse | ExecuteResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    api.health()
      .then(() => { setOnline(true); setApiError(null); })
      .catch(() => { setOnline(false); setApiError("Local API is unavailable. Start FastAPI on 127.0.0.1:8000 and try again."); });
  }, []);

  async function parsePreview() {
    setLoading("parse"); setMessage(null); setApiError(null);
    try {
      const result = await api.parse(prompt);
      setResponse(result);
      setMessage(result.success ? "Prompt parsed and validated successfully." : result.error);
      setOnline(true);
    } catch (error) {
      setOnline(false); setApiError(error instanceof Error ? error.message : "Unable to reach the local API.");
    } finally { setLoading(null); }
  }

  async function executeDryRun() {
    setLoading("execute"); setMessage(null); setApiError(null);
    try {
      const result = await api.execute(prompt, "dry_run", true);
      setResponse(result); setMessage("Dry-run completed safely. No SolidWorks operation was triggered."); setOnline(true);
    } catch (error) {
      setOnline(false); setApiError(error instanceof Error ? error.message : "Dry-run request failed.");
    } finally { setLoading(null); }
  }

  const execution = response && "logs" in response ? response : null;
  const valid = response?.success ?? false;

  return <main className="shell"><div className="workspace">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Box size={23}/></div><div><h1>Prompt-to-CAD</h1><p className="subtitle">Local SolidWorks Automation</p></div></div>
      <div className="status"><span className={`dot ${online === true ? "online" : online === false ? "offline" : ""}`}/><span>{online === null ? "Checking backend" : online ? "Backend online" : "Backend unavailable"}</span></div>
    </header>

    <section className="panel composer">
      <div className="section-label">Natural-language command</div>
      <h2 style={{ fontSize: 20, marginBottom: 14 }}>Describe the part to create</h2>
      <textarea className="prompt" value={prompt} onChange={event => setPrompt(event.target.value)} aria-label="CAD command" />
      <div className="templates">{templates.map(template => <button className="template" key={template.label} onClick={() => setPrompt(template.prompt)} disabled={loading !== null}>{template.label}</button>)}</div>
      <div className="actions">
        <button className="button" onClick={parsePreview} disabled={loading !== null || !prompt.trim()}>{loading === "parse" ? <LoaderCircle size={17}/> : <ScanSearch size={17}/>}Parse &amp; Preview</button>
        <button className="button primary" onClick={executeDryRun} disabled={loading !== null || !prompt.trim()}>{loading === "execute" ? <LoaderCircle size={17}/> : <Play size={17}/>}Run Dry-Run</button>
      </div>
      {apiError && <div className="error-banner"><CircleAlert size={15} style={{ verticalAlign: "text-bottom", marginRight: 8 }}/>{apiError}</div>}
    </section>

    <section className="results" aria-live="polite">
      <article className="panel result-card"><div className="section-label">Intent</div><h3><Braces size={15} style={{ verticalAlign: "text-bottom", marginRight: 7 }}/>Parsed intent JSON</h3>{response?.parsed_intent ? <pre>{JSON.stringify(response.parsed_intent, null, 2)}</pre> : <p className="empty">Parse a command to inspect its deterministic intent.</p>}</article>
      <article className="panel result-card"><div className="section-label">Validation</div><h3>Schema state</h3>{response ? <><div className={`validation ${valid ? "ok" : "bad"}`}>{valid ? <CheckCircle2 size={18}/> : <CircleAlert size={18}/>} {valid ? "Intent accepted" : "Intent rejected"}</div><p className="muted" style={{ fontSize: 12, marginTop: 12 }}>{response.error || "Dimensions and parameters satisfy the Pydantic schema."}</p></> : <p className="empty">Validation has not run yet.</p>}</article>
      <article className="panel result-card"><div className="section-label">Execution</div><h3>Operation log</h3>{execution?.logs.length ? <ul className="logs">{execution.logs.map((line, index) => <li key={`${line}-${index}`}>{line}</li>)}</ul> : <p className="empty">Dry-run logs will appear here.</p>}</article>
      <article className="panel result-card"><div className="section-label">Result</div><h3>Request outcome</h3>{message ? <><p className={valid ? "success" : "failure"}>{message}</p>{execution?.result && <pre>{JSON.stringify(execution.result, null, 2)}</pre>}</> : <p className="empty">No request has completed.</p>}</article>
    </section>
  </div></main>;
}
