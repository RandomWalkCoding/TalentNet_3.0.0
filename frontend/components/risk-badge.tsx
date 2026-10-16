import { RISK_LEVEL_CLASSES, RISK_LEVEL_LABELS } from "@/lib/labels";

export function RiskBadge({ level }: { level: string | null }) {
  if (!level) {
    return (
      <span className="inline-flex rounded-md border border-slate-300 bg-slate-100 px-2 py-1 text-xs font-bold text-slate-600">
        未评分
      </span>
    );
  }

  return (
    <span
      className={`inline-flex rounded-md border px-2 py-1 text-xs font-black ${
        RISK_LEVEL_CLASSES[level] ?? RISK_LEVEL_CLASSES.needs_review
      }`}
    >
      {RISK_LEVEL_LABELS[level] ?? level}
    </span>
  );
}
