"use client";

import { Crosshair } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { addCandidateToPool } from "@/lib/api";

export function AddToPoolButton({ candidateId }: { candidateId: string }) {
  const router = useRouter();
  const [isAdding, setIsAdding] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function onAdd() {
    if (isAdding) return;
    setIsAdding(true);
    setMessage(null);
    try {
      await addCandidateToPool(candidateId);
      setMessage("已加入人才猎场");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "加入失败");
    } finally {
      setIsAdding(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-2 lg:items-end">
      <button
        type="button"
        onClick={onAdd}
        disabled={isAdding}
        className="tn-button tn-button-primary"
      >
        <Crosshair className="h-4 w-4" />
        {isAdding ? "加入中" : "加入人才猎场"}
      </button>
      {message ? <p className="text-xs font-semibold text-muted-foreground">{message}</p> : null}
    </div>
  );
}
