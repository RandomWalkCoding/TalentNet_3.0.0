"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createFeedback } from "@/lib/api";
import { OUTCOME_LABELS } from "@/lib/labels";

const QUICK_OUTCOMES = ["contacted", "no_response", "interested", "bad_prediction"];

export function QuickFeedbackControl({ candidateId }: { candidateId: string }) {
  const router = useRouter();
  const [outcome, setOutcome] = useState("contacted");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onSubmit() {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      await createFeedback({
        candidate_id: candidateId,
        outcome,
        contact_channel: "linkedin",
        note: "人才猎场快速反馈"
      });
      router.refresh();
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <select
        value={outcome}
        onChange={(event) => setOutcome(event.target.value)}
        className="tn-field min-w-28 px-2 py-1"
      >
        {QUICK_OUTCOMES.map((item) => (
          <option key={item} value={item}>
            {OUTCOME_LABELS[item]}
          </option>
        ))}
      </select>
      <button
        type="button"
        disabled={isSubmitting}
        onClick={onSubmit}
        className="tn-button tn-button-secondary min-h-8 px-2 py-1"
      >
        记录
      </button>
    </div>
  );
}
