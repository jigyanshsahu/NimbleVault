"use client";

import React from "react";
import { type JobStatus } from "@/lib/api";
import clsx from "clsx";

interface Props {
  status: JobStatus;
}

const CONFIG: Record<
  JobStatus,
  { label: string; dot: string; bg: string; text: string; glow: string }
> = {
  PENDING: {
    label: "Pending",
    dot: "bg-slate-400",
    bg: "bg-slate-400/10 border-slate-400/30",
    text: "text-slate-300",
    glow: "",
  },
  DOWNLOADING: {
    label: "Downloading",
    dot: "bg-cyan-400 animate-pulse",
    bg: "bg-cyan-400/10 border-cyan-400/30",
    text: "text-cyan-300",
    glow: "shadow-[0_0_8px_rgba(6,182,212,0.4)]",
  },
  TITLING: {
    label: "AI Titling",
    dot: "bg-violet-400 animate-pulse",
    bg: "bg-violet-400/10 border-violet-400/30",
    text: "text-violet-300",
    glow: "shadow-[0_0_8px_rgba(124,58,237,0.4)]",
  },
  UPLOADING: {
    label: "Uploading",
    dot: "bg-brand-400 animate-pulse",
    bg: "bg-brand-400/10 border-brand-400/30",
    text: "text-brand-300",
    glow: "shadow-[0_0_8px_rgba(77,123,255,0.4)]",
  },
  COMPLETED: {
    label: "Completed",
    dot: "bg-emerald-400",
    bg: "bg-emerald-400/10 border-emerald-400/30",
    text: "text-emerald-300",
    glow: "",
  },
  FAILED: {
    label: "Failed",
    dot: "bg-rose-500",
    bg: "bg-rose-500/10 border-rose-500/30",
    text: "text-rose-300",
    glow: "",
  },
};

export const StatusBadge: React.FC<Props> = ({ status }) => {
  const c = CONFIG[status] ?? CONFIG.PENDING;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold tracking-wide",
        c.bg,
        c.text,
        c.glow,
      )}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full", c.dot)} />
      {c.label}
    </span>
  );
};
