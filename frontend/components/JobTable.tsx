"use client";

import React, { useState, useCallback } from "react";
import {
  ExternalLink,
  Pencil,
  Check,
  X,
  Play,
  Loader2,
  AlertCircle,
  FileVideo,
  Layers,
} from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { updateJobTitle, processJob } from "@/lib/api";
import type { VideoJob } from "@/lib/api";
import clsx from "clsx";

interface Props {
  jobs: VideoJob[];
  onJobsChange: (updater: (prev: VideoJob[]) => VideoJob[]) => void;
}

interface EditState {
  jobId: string;
  value: string;
}

const ACTIVE_STATUSES = new Set(["DOWNLOADING", "TITLING", "UPLOADING"]);

export const JobTable: React.FC<Props> = ({ jobs, onJobsChange }) => {
  const [editState, setEditState] = useState<EditState | null>(null);
  const [savingTitle, setSavingTitle] = useState<string | null>(null);
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());
  const [expandedError, setExpandedError] = useState<string | null>(null);

  // ── Inline title editing ─────────────────────────────────────────────────

  const startEdit = (job: VideoJob) => {
    if (ACTIVE_STATUSES.has(job.status)) return;
    setEditState({ jobId: job.id, value: job.generated_title ?? "" });
  };

  const cancelEdit = () => setEditState(null);

  const commitEdit = useCallback(async () => {
    if (!editState) return;
    setSavingTitle(editState.jobId);
    try {
      const updated = await updateJobTitle(editState.jobId, editState.value);
      onJobsChange((prev) =>
        prev.map((j) => (j.id === updated.id ? updated : j)),
      );
    } catch {
      // silently re-use old value on error
    } finally {
      setSavingTitle(null);
      setEditState(null);
    }
  }, [editState, onJobsChange]);

  // ── Single job processing ────────────────────────────────────────────────

  const handleProcess = async (jobId: string) => {
    setProcessingIds((prev) => new Set([...prev, jobId]));
    try {
      await processJob(jobId);
    } catch (err) {
      console.error("Process job error:", err);
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(jobId);
        return next;
      });
    }
  };

  // ── Empty state ──────────────────────────────────────────────────────────

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-white/10 bg-dark-800/40 py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-dark-700/60 ring-1 ring-white/10">
          <Layers className="h-7 w-7 text-slate-500" />
        </div>
        <p className="text-sm font-medium text-slate-400">No jobs yet</p>
        <p className="text-xs text-slate-600">
          Scan a Google Drive folder to discover videos
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-white/[0.08] bg-dark-800/70 shadow-glass backdrop-blur-xl">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.06] bg-dark-700/40">
              <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                File Path
              </th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                AI Title
              </th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                Status
              </th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                YouTube
              </th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {jobs.map((job) => {
              const isEditing = editState?.jobId === job.id;
              const isSaving = savingTitle === job.id;
              const isProcessing = processingIds.has(job.id);
              const isActive = ACTIVE_STATUSES.has(job.status);
              const canProcess =
                job.status === "PENDING" || job.status === "FAILED";

              return (
                <tr
                  key={job.id}
                  className="group transition-colors hover:bg-white/[0.02]"
                >
                  {/* File path */}
                  <td className="max-w-[240px] px-5 py-4">
                    <div className="flex items-start gap-2">
                      <FileVideo className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                      <div className="min-w-0">
                        <p className="truncate font-medium text-white">
                          {job.file_name}
                        </p>
                        <p
                          className="truncate text-xs text-slate-500"
                          title={job.full_path}
                        >
                          {job.full_path}
                        </p>
                      </div>
                    </div>
                  </td>

                  {/* AI title – inline editable */}
                  <td className="max-w-[280px] px-5 py-4">
                    {isEditing ? (
                      <div className="flex items-center gap-2">
                        <input
                          id={`title-edit-${job.id}`}
                          autoFocus
                          value={editState.value}
                          onChange={(e) =>
                            setEditState((s) =>
                              s ? { ...s, value: e.target.value } : null,
                            )
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") commitEdit();
                            if (e.key === "Escape") cancelEdit();
                          }}
                          className="flex-1 rounded-lg border border-brand-500/40 bg-dark-700 px-3 py-1.5 text-xs text-white outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/30"
                        />
                        <button
                          id={`title-save-${job.id}`}
                          onClick={commitEdit}
                          disabled={isSaving}
                          className="rounded-lg bg-brand-500/20 p-1.5 text-brand-400 hover:bg-brand-500/40"
                        >
                          {isSaving ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Check className="h-3.5 w-3.5" />
                          )}
                        </button>
                        <button
                          id={`title-cancel-${job.id}`}
                          onClick={cancelEdit}
                          className="rounded-lg bg-white/5 p-1.5 text-slate-400 hover:bg-white/10"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span
                          className={clsx(
                            "flex-1 truncate text-xs",
                            job.generated_title
                              ? "text-slate-200"
                              : "italic text-slate-600",
                          )}
                          title={job.generated_title ?? undefined}
                        >
                          {job.generated_title ?? "—"}
                        </span>
                        {!isActive && (
                          <button
                            id={`title-edit-btn-${job.id}`}
                            onClick={() => startEdit(job)}
                            className="shrink-0 rounded-md p-1 text-slate-600 opacity-0 transition-all hover:bg-white/10 hover:text-slate-300 group-hover:opacity-100"
                            title="Edit title"
                          >
                            <Pencil className="h-3 w-3" />
                          </button>
                        )}
                      </div>
                    )}

                    {/* Error tooltip */}
                    {job.status === "FAILED" && job.error_log && (
                      <div className="mt-1.5">
                        <button
                          id={`error-toggle-${job.id}`}
                          onClick={() =>
                            setExpandedError((prev) =>
                              prev === job.id ? null : job.id,
                            )
                          }
                          className="flex items-center gap-1 text-xs text-rose-400 hover:text-rose-300"
                        >
                          <AlertCircle className="h-3 w-3" />
                          {expandedError === job.id ? "Hide error" : "View error"}
                        </button>
                        {expandedError === job.id && (
                          <pre className="mt-1.5 max-h-24 overflow-auto rounded-lg bg-rose-500/10 p-2 text-xs text-rose-300">
                            {job.error_log}
                          </pre>
                        )}
                      </div>
                    )}
                  </td>

                  {/* Status badge */}
                  <td className="px-5 py-4">
                    <StatusBadge status={job.status} />
                  </td>

                  {/* YouTube link */}
                  <td className="px-5 py-4">
                    {job.youtube_url ? (
                      <a
                        id={`yt-link-${job.id}`}
                        href={job.youtube_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-lg bg-rose-500/10 px-3 py-1.5 text-xs font-semibold text-rose-400 ring-1 ring-rose-500/20 transition-all hover:bg-rose-500/20 hover:ring-rose-500/40"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Watch
                      </a>
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                  </td>

                  {/* Action button */}
                  <td className="px-5 py-4">
                    {isActive ? (
                      <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Processing
                      </span>
                    ) : canProcess ? (
                      <button
                        id={`process-btn-${job.id}`}
                        onClick={() => handleProcess(job.id)}
                        disabled={isProcessing}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-brand-500/15 px-3 py-1.5 text-xs font-semibold text-brand-400 ring-1 ring-brand-500/25 transition-all hover:bg-brand-500/30 hover:ring-brand-500/50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isProcessing ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Play className="h-3.5 w-3.5" />
                        )}
                        {job.status === "FAILED" ? "Retry" : "Process"}
                      </button>
                    ) : (
                      <span className="text-xs text-emerald-500">✓ Done</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
