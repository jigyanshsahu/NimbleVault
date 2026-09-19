"use client";

import React, { useState } from "react";
import { FolderSearch, Loader2, Sparkles } from "lucide-react";
import { scanFolder } from "@/lib/api";
import type { VideoJob } from "@/lib/api";

interface Props {
  onScanComplete: (jobs: VideoJob[]) => void;
  onError: (msg: string) => void;
}

export const FolderScanner: React.FC<Props> = ({ onScanComplete, onError }) => {
  const [folderId, setFolderId] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastCount, setLastCount] = useState<number | null>(null);

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!folderId.trim()) return;

    setLoading(true);
    setLastCount(null);

    try {
      const newJobs = await scanFolder(folderId.trim());
      setLastCount(newJobs.length);
      onScanComplete(newJobs);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-dark-800/70 p-6 shadow-glass backdrop-blur-xl">
      {/* Decorative gradient blob */}
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-brand-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-16 -left-16 h-40 w-40 rounded-full bg-accent-purple/10 blur-3xl" />

      <div className="relative">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/20 ring-1 ring-brand-500/30">
            <FolderSearch className="h-5 w-5 text-brand-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Folder Scanner</h2>
            <p className="text-xs text-slate-400">
              Recursively discover all videos in a Google Drive folder
            </p>
          </div>
        </div>

        <form onSubmit={handleScan} className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <input
              type="text"
              id="folder-id-input"
              value={folderId}
              onChange={(e) => setFolderId(e.target.value)}
              placeholder="e.g. 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74"
              disabled={loading}
              className="w-full rounded-xl border border-white/10 bg-dark-700/80 px-4 py-3 pr-12 text-sm text-white placeholder-slate-500 outline-none ring-0 transition-all focus:border-brand-500/60 focus:ring-2 focus:ring-brand-500/20 disabled:opacity-50"
              aria-label="Google Drive Folder ID"
            />
            <FolderSearch className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          </div>

          <button
            type="submit"
            id="scan-folder-button"
            disabled={loading || !folderId.trim()}
            className="group relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-xl bg-brand-500 px-6 py-3 text-sm font-semibold text-white shadow-glow transition-all hover:bg-brand-400 hover:shadow-[0_0_30px_rgba(37,88,255,0.5)] focus:outline-none focus:ring-2 focus:ring-brand-500/50 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
          >
            <span className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 opacity-0 transition-opacity group-hover:opacity-100" />
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Scanning…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Scan Folder
              </>
            )}
          </button>
        </form>

        {lastCount !== null && !loading && (
          <p className="mt-3 animate-fade-in text-xs text-slate-400">
            {lastCount === 0
              ? "✓ No new videos found (all already tracked)"
              : `✓ Added ${lastCount} new video${lastCount !== 1 ? "s" : ""} to the pipeline`}
          </p>
        )}
      </div>
    </div>
  );
};
