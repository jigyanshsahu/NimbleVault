/**
 * NimbleVault – Typed API client
 * All communication with the FastAPI backend goes through this module.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Shared types ──────────────────────────────────────────────────────────────

export type JobStatus =
  | "PENDING"
  | "DOWNLOADING"
  | "TITLING"
  | "UPLOADING"
  | "COMPLETED"
  | "FAILED";

export interface VideoJob {
  id: string;
  drive_file_id: string;
  file_name: string;
  full_path: string;
  generated_title: string | null;
  youtube_video_id: string | null;
  youtube_url: string | null;
  status: JobStatus;
  error_log: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScanResult {
  jobs: VideoJob[];
}

export interface BatchResult {
  message: string;
  queued: number;
  job_ids?: string[];
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── API functions ─────────────────────────────────────────────────────────────

/** Recursively scan a Drive folder and persist discovered videos as PENDING jobs. */
export async function scanFolder(folderId: string): Promise<VideoJob[]> {
  return apiFetch<VideoJob[]>("/api/scan", {
    method: "POST",
    body: JSON.stringify({ folder_id: folderId }),
  });
}

/** Fetch all video jobs (sorted newest first). */
export async function fetchJobs(): Promise<VideoJob[]> {
  return apiFetch<VideoJob[]>("/api/jobs");
}

/** Update the AI-generated title for a job before upload. */
export async function updateJobTitle(
  jobId: string,
  title: string,
): Promise<VideoJob> {
  return apiFetch<VideoJob>(`/api/jobs/${jobId}/title`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

/** Trigger the full processing pipeline for a single job. */
export async function processJob(jobId: string): Promise<{ message: string; job_id: string }> {
  return apiFetch(`/api/process/${jobId}`, { method: "POST" });
}

/** Trigger sequential batch processing for all PENDING jobs. */
export async function processBatch(): Promise<BatchResult> {
  return apiFetch<BatchResult>("/api/process-batch", { method: "POST" });
}
