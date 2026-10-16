"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { updateTalentPoolItem } from "@/lib/api";

const STATUS_OPTIONS = [
  { value: "watching", label: "观察中" },
  { value: "contacted", label: "已触达" },
  { value: "in_process", label: "流程中" },
  { value: "closed", label: "已关闭" }
];

export function TalentPoolStatusControl({
  itemId,
  status
}: {
  itemId: string;
  status: string;
}) {
  const router = useRouter();
  const [isUpdating, setIsUpdating] = useState(false);

  async function onChange(nextStatus: string) {
    if (isUpdating || nextStatus === status) return;
    setIsUpdating(true);
    try {
      await updateTalentPoolItem(itemId, { status: nextStatus });
      router.refresh();
    } finally {
      setIsUpdating(false);
    }
  }

  return (
    <select
      value={status}
      disabled={isUpdating}
      onChange={(event) => onChange(event.target.value)}
      className="tn-field min-w-24 px-2 py-1 disabled:opacity-60"
    >
      {STATUS_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
