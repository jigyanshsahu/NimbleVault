"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  CheckCircle2,
  ChevronRight,
  Circle,
  Clapperboard,
  Clock,
  HardDriveDownload,
  Layers,
  Loader2,
  RefreshCw,
  Rocket,
  Sparkles,
  Tv2,
  Upload,
  XCircle,
  Zap,
} from "lucide-react";
import { FolderScanner } from "@/components/FolderScanner";
import { JobTable } from "@/components/JobTable";
import { processBatch, fetchJobs, syncYouTubeStatus } from "@/lib/api";
import type { VideoJob, JobStatus } from "@/lib/api";
import clsx from "clsx";

// ── Polling interval (ms) ─────────────────────────────────────────────────────
const POLL_INTERVAL = 3000;

// ── Status counts helper ──────────────────────────────────────────────────────
function computeStats(jobs: VideoJob[]) {
  return {
    total: jobs.length,
    pending: jobs.filter((j) => j.status === "PENDING").length,
    active: jobs.filter((j) =>
      ["DOWNLOADING", "TITLING", "UPLOADING"].includes(j.status),
    ).length,
    completed: jobs.filter((j) => j.status === "COMPLETED").length,
    failed: jobs.filter((j) => j.status === "FAILED").length,
  };
}

// ── Stat card component ───────────────────────────────────────────────────────
interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
  glow?: string;
  pulse?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({
  icon,
  label,
  value,
  color,
  glow,
  pulse,
}) => (
  <div
    className={clsx(
      "relative overflow-hidden rounded-2xl border border-white/[0.06] bg-dark-800/60 p-5 backdrop-blur-sm",
      glow,
    )}
  >
    <div className="flex items-start justify-between">
      <div>
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <p className={clsx("mt-1.5 text-3xl font-bold tabular-nums", color)}>
          {value}
        </p>
      </div>
      <div
        className={clsx(
          "flex h-10 w-10 items-center justify-center rounded-xl bg-white/5",
          pulse && value > 0 && "animate-pulse-slow",
        )}
      >
        {icon}
      </div>
    </div>
  </div>
);

// ── Toast notification ────────────────────────────────────────────────────────
interface Toast {
  id: string;
  type: "success" | "error" | "info";
  message: string;
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function HomePage() {
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [isPolling, setIsPolling] = useState(true);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Toast helpers ────────────────────────────────────────────────────────

  const addToast = useCallback(
    (type: Toast["type"], message: string) => {
      const id = Math.random().toString(36).slice(2);
      setToasts((prev) => [...prev, { id, type, message }]);
      setTimeout(
        () => setToasts((prev) => prev.filter((t) => t.id !== id)),
        4000,
      );
    },
    [],
  );

  // ── Jobs loader ──────────────────────────────────────────────────────────

  const loadJobs = useCallback(async (silent = false) => {
    if (!silent) setIsLoadingJobs(true);
    try {
      const data = await fetchJobs();
      setJobs(data);
      setLastRefresh(new Date());
    } catch (err) {
      if (!silent) {
        addToast("error", err instanceof Error ? err.message : "Failed to load jobs");
      }
    } finally {
      if (!silent) setIsLoadingJobs(false);
    }
  }, [addToast]);

  // ── Polling ──────────────────────────────────────────────────────────────

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    if (!isPolling) {
      if (pollingRef.current) clearInterval(pollingRef.current);
      return;
    }

    pollingRef.current = setInterval(() => {
      loadJobs(true /* silent */);
    }, POLL_INTERVAL);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [isPolling, loadJobs]);

  // ── Scan complete handler ────────────────────────────────────────────────

  const handleScanComplete = useCallback(
    (newJobs: VideoJob[]) => {
      setJobs((prev) => {
        const existingIds = new Set(prev.map((j) => j.id));
        const truly_new = newJobs.filter((j) => !existingIds.has(j.id));
        return [...truly_new, ...prev];
      });
      addToast(
        "success",
        newJobs.length === 0
          ? "Scan complete – no new videos found"
          : `Added ${newJobs.length} new video${newJobs.length !== 1 ? "s" : ""} to the pipeline`,
      );
    },
    [addToast],
  );

  // ── Batch process handler ────────────────────────────────────────────────

  const handleBatchProcess = async () => {
    setIsBatchProcessing(true);
    try {
      const result = await processBatch();
      addToast(
        "info",
        result.queued === 0
          ? "No pending jobs to process"
          : `Batch started: ${result.queued} job${result.queued !== 1 ? "s" : ""} queued`,
      );
    } catch (err) {
      addToast("error", err instanceof Error ? err.message : "Batch failed");
    } finally {
      setIsBatchProcessing(false);
    }
  };

  // ── Sync YouTube handler ─────────────────────────────────────────────────

  const handleSyncYouTube = async () => {
    setIsSyncing(true);
    try {
      const result = await syncYouTubeStatus();
      if (result.reconciled_count > 0) {
        addToast(
          "info",
          `Reconciled ${result.reconciled_count} desynced video(s) deleted on YouTube back to PENDING.`,
        );
      } else {
        addToast("success", "Audit complete: All completed videos are active on YouTube.");
      }
      await loadJobs(true);
    } catch (err) {
      addToast("error", err instanceof Error ? err.message : "YouTube audit failed");
    } finally {
      setIsSyncing(false);
    }
  };

  // ── Jobs update handler (for child mutations) ────────────────────────────

  const handleJobsChange = useCallback(
    (updater: (prev: VideoJob[]) => VideoJob[]) => {
      setJobs(updater);
    },
    [],
  );

  const stats = computeStats(jobs);
  const hasActiveJobs = stats.active > 0;

  return (
    <div className="gradient-bg noise relative min-h-screen">
      {/* ── Toast container ────────────────────────────────────────────── */}
      <div className="fixed right-4 top-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={clsx(
              "animate-slide-up flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-medium shadow-xl backdrop-blur-xl",
              t.type === "success" &&
                "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
              t.type === "error" &&
                "border-rose-500/30 bg-rose-500/10 text-rose-300",
              t.type === "info" &&
                "border-brand-500/30 bg-brand-500/10 text-brand-300",
            )}
          >
            {t.type === "success" && <CheckCircle2 className="h-4 w-4 shrink-0" />}
            {t.type === "error" && <XCircle className="h-4 w-4 shrink-0" />}
            {t.type === "info" && <Zap className="h-4 w-4 shrink-0" />}
            {t.message}
          </div>
        ))}
      </div>

      <div className="mx-auto max-w-screen-xl px-4 pb-16 pt-6 sm:px-6 lg:px-8">
        {/* ── Header ────────────────────────────────────────────────────── */}
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            {/* Logo mark */}
            <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-400 to-accent-purple shadow-glow">
              <Clapperboard className="h-6 w-6 text-white" />
              <div className="absolute inset-0 rounded-2xl ring-1 ring-white/20" />
            </div>

            <div>
              <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-white">
                NimbleVault
                <span className="rounded-full bg-brand-500/20 px-2 py-0.5 text-xs font-semibold text-brand-400 ring-1 ring-brand-500/30">
                  v1.0
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                AI-powered video pipeline · Drive → Gemini → YouTube
              </p>
            </div>
          </div>

          {/* Status indicators */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Live indicator */}
            <div
              className={clsx(
                "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium",
                hasActiveJobs
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                  : "border-white/10 bg-white/5 text-slate-400",
              )}
            >
              <span
                className={clsx(
                  "h-1.5 w-1.5 rounded-full",
                  hasActiveJobs
                    ? "animate-pulse bg-emerald-400"
                    : "bg-slate-500",
                )}
              />
              {hasActiveJobs ? "Pipeline Active" : "Idle"}
            </div>

            {/* Polling toggle */}
            <button
              id="polling-toggle"
              onClick={() => setIsPolling((p) => !p)}
              title={isPolling ? "Pause auto-refresh" : "Resume auto-refresh"}
              className={clsx(
                "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all",
                isPolling
                  ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-400"
                  : "border-white/10 bg-white/5 text-slate-500",
              )}
            >
              <Activity className={clsx("h-3.5 w-3.5", isPolling && "animate-pulse-slow")} />
              {isPolling ? "Live" : "Paused"}
            </button>

            {/* Last refresh */}
            {lastRefresh && (
              <span className="flex items-center gap-1 text-xs text-slate-600">
                <Clock className="h-3 w-3" />
                {lastRefresh.toLocaleTimeString()}
              </span>
            )}

            {/* Manual refresh */}
            <button
              id="manual-refresh"
              onClick={() => loadJobs()}
              disabled={isLoadingJobs}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-400 transition-all hover:border-white/20 hover:bg-white/10 hover:text-white disabled:opacity-50"
            >
              <RefreshCw
                className={clsx("h-3.5 w-3.5", isLoadingJobs && "animate-spin")}
              />
            </button>
          </div>
        </header>

        {/* ── Stats row ─────────────────────────────────────────────────── */}
        <section
          className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
          aria-label="Pipeline statistics"
        >
          <StatCard
            icon={<Layers className="h-5 w-5 text-slate-400" />}
            label="Total Jobs"
            value={stats.total}
            color="text-white"
          />
          <StatCard
            icon={<Circle className="h-5 w-5 text-brand-400" />}
            label="Pending"
            value={stats.pending}
            color="text-brand-300"
            glow={
              stats.pending > 0
                ? "ring-1 ring-brand-500/20"
                : ""
            }
          />
          <StatCard
            icon={<Rocket className="h-5 w-5 text-violet-400" />}
            label="Active"
            value={stats.active}
            color="text-violet-300"
            pulse
            glow={
              stats.active > 0
                ? "ring-1 ring-violet-500/20 shadow-[0_0_20px_rgba(124,58,237,0.15)]"
                : ""
            }
          />
          <StatCard
            icon={<CheckCircle2 className="h-5 w-5 text-emerald-400" />}
            label="Completed"
            value={stats.completed}
            color="text-emerald-300"
          />
        </section>

        {/* ── Folder Scanner Card ────────────────────────────────────────── */}
        <section className="mb-6">
          <FolderScanner
            onScanComplete={handleScanComplete}
            onError={(msg) => addToast("error", msg)}
          />
        </section>

        {/* ── Job Dashboard ──────────────────────────────────────────────── */}
        <section>
          {/* Dashboard header row */}
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="flex items-center gap-2 text-base font-semibold text-white">
                <Tv2 className="h-4 w-4 text-brand-400" />
                Video Pipeline
                {isLoadingJobs && (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" />
                )}
              </h2>
              <p className="text-xs text-slate-500">
                Auto-refreshes every {POLL_INTERVAL / 1000}s · {stats.total} total job
                {stats.total !== 1 ? "s" : ""}
              </p>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-3">
              <button
                id="sync-youtube-button"
                onClick={handleSyncYouTube}
                disabled={isSyncing}
                title="Verify all completed videos on YouTube and auto-reconcile deleted videos back to PENDING"
                className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-semibold text-slate-300 transition-all hover:border-white/20 hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RefreshCw
                  className={clsx("h-4 w-4", isSyncing && "animate-spin text-brand-400")}
                />
                {isSyncing ? "Auditing YouTube…" : "Sync YouTube"}
              </button>

              <button
                id="process-all-button"
                onClick={handleBatchProcess}
                disabled={isBatchProcessing || stats.pending === 0}
                className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand-500 to-accent-purple px-5 py-2.5 text-sm font-semibold text-white shadow-glow transition-all hover:shadow-[0_0_30px_rgba(37,88,255,0.5)] disabled:cursor-not-allowed disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-400 disabled:shadow-none"
              >
                {isBatchProcessing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Processing…
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4" />
                    Process All Pending
                    {stats.pending > 0 && (
                      <span className="rounded-full bg-white/20 px-1.5 py-0.5 text-xs">
                        {stats.pending}
                      </span>
                    )}
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Pipeline legend */}
          <div className="mb-4 flex flex-wrap gap-4 text-xs text-slate-500">
            {[
              { icon: <HardDriveDownload className="h-3 w-3" />, label: "Download from Drive", color: "text-cyan-500" },
              { icon: <Sparkles className="h-3 w-3" />, label: "AI title via Gemini", color: "text-violet-500" },
              { icon: <Upload className="h-3 w-3" />, label: "Upload to YouTube", color: "text-brand-400" },
            ].map(({ icon, label, color }) => (
              <span key={label} className={clsx("flex items-center gap-1.5", color)}>
                {icon}
                <ChevronRight className="h-2.5 w-2.5 text-slate-600" />
                <span className="text-slate-500">{label}</span>
              </span>
            ))}
          </div>

          {/* The table */}
          {isLoadingJobs && jobs.length === 0 ? (
            <div className="overflow-hidden rounded-2xl border border-white/[0.06] bg-dark-800/60 backdrop-blur-sm">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="shimmer border-b border-white/[0.04] px-5 py-5"
                  style={{ animationDelay: `${i * 0.1}s` }}
                >
                  <div className="flex items-center gap-4">
                    <div className="h-3 w-48 rounded-full bg-white/5" />
                    <div className="h-3 w-64 rounded-full bg-white/5" />
                    <div className="ml-auto h-5 w-20 rounded-full bg-white/5" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <JobTable jobs={jobs} onJobsChange={handleJobsChange} />
          )}
        </section>
      </div>
    </div>
  );
}
