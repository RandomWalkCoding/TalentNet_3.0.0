"use client";

import { Send } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { createFeedback, type Feedback } from "@/lib/api";
import { CONTACT_CHANNEL_LABELS, OUTCOME_LABELS } from "@/lib/labels";

const OUTCOMES = [
  "contacted",
  "no_response",
  "rejected",
  "not_interested",
  "interested",
  "in_process",
  "offer_sent",
  "hired",
  "bad_prediction"
];

const CHANNELS = ["linkedin", "maimai", "email", "phone", "wechat", "other"];

export function FeedbackPanel({
  candidateId,
  feedback
}: {
  candidateId: string;
  feedback: Feedback[];
}) {
  const router = useRouter();
  const [outcome, setOutcome] = useState("contacted");
  const [contactChannel, setContactChannel] = useState("linkedin");
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await createFeedback({
        candidate_id: candidateId,
        outcome,
        contact_channel: contactChannel,
        note
      });
      setNote("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "记录反馈失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <form className="tn-surface rounded-lg p-5" onSubmit={onSubmit}>
        <h2 className="font-black">记录反馈</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          将触达结果写回后端，形成坏例和转化闭环。
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <select value={outcome} onChange={(event) => setOutcome(event.target.value)} className="tn-field">
            {OUTCOMES.map((item) => (
              <option key={item} value={item}>
                {OUTCOME_LABELS[item]}
              </option>
            ))}
          </select>
          <select
            value={contactChannel}
            onChange={(event) => setContactChannel(event.target.value)}
            className="tn-field"
          >
            {CHANNELS.map((item) => (
              <option key={item} value={item}>
                {CONTACT_CHANNEL_LABELS[item]}
              </option>
            ))}
          </select>
        </div>
        <textarea
          value={note}
          onChange={(event) => setNote(event.target.value)}
          rows={4}
          placeholder="记录候选人反馈、原话或判断偏差"
          className="tn-field mt-3"
        />
        <div className="mt-3 flex items-center justify-between gap-3">
          {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : <span />}
          <button type="submit" disabled={isSubmitting} className="tn-button tn-button-primary">
            <Send className="h-4 w-4" />
            {isSubmitting ? "提交中" : "记录反馈"}
          </button>
        </div>
      </form>

      <div className="tn-surface rounded-lg">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="font-black">反馈历史</h2>
          <span className="text-sm font-bold text-muted-foreground">{feedback.length} 条</span>
        </div>
        <div className="divide-y divide-border">
          {feedback.length > 0 ? (
            feedback.map((item) => (
              <article key={item.id} className="px-5 py-4 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-black">{OUTCOME_LABELS[item.outcome] ?? item.outcome}</p>
                  <span className="text-xs text-muted-foreground">
                    {new Date(item.created_at).toLocaleString("zh-CN")}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.contact_channel
                    ? CONTACT_CHANNEL_LABELS[item.contact_channel] ?? item.contact_channel
                    : "未记录渠道"}
                </p>
                {item.note ? <p className="mt-2 leading-6">{item.note}</p> : null}
              </article>
            ))
          ) : (
            <p className="px-5 py-8 text-sm text-muted-foreground">
              暂无反馈。触达候选人后在这里补全 Outcome。
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
