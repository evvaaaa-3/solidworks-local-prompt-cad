export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export interface HealthResponse { status: string; service: string }
export interface OutputFile {
  filename: string; file_type: string; category: "parts" | "exports";
  relative_path: string; size_bytes: number; modified_time: string;
}
export interface ParseResponse {
  success: boolean; raw_prompt: string;
  parsed_intent: Record<string, unknown> | null;
  validated_intent: Record<string, unknown> | null;
  error: string | null;
}
export interface ExecuteResponse extends ParseResponse {
  mode: "dry_run" | "real";
  result: Record<string, unknown> | null;
  logs: string[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.detail || "API request failed");
  return data as T;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  outputs: () => request<OutputFile[]>("/api/outputs"),
  parse: (prompt: string) => request<ParseResponse>("/api/parse", {
    method: "POST", body: JSON.stringify({ prompt }),
  }),
  execute: (prompt: string, mode: "dry_run" | "real", confirmed: boolean) =>
    request<ExecuteResponse>("/api/execute", {
      method: "POST", body: JSON.stringify({ prompt, mode, confirmed }),
    }),
  outputUrl: (file: OutputFile) =>
    `${API_BASE_URL}/api/outputs/${file.category}/${encodeURIComponent(file.filename)}`,
};
