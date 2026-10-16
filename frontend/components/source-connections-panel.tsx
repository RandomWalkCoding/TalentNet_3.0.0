"use client";

import { Link2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { updateSourceConnection, type SourceConnection } from "@/lib/api";

export function SourceConnectionsPanel({ connections }: { connections: SourceConnection[] }) {
  const router = useRouter();
  const [items, setItems] = useState(connections);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function setStatus(provider: string, status: string) {
    setBusy(provider);
    setError(null);
    try {
      const updated = await updateSourceConnection(provider, status);
      setItems((current) =>
        current.map((item) => (item.provider === provider ? updated : item))
      );
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新数据源状态失败");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="tn-surface rounded-lg p-5">
      <div className="mb-4 flex items-center gap-2">
        <Link2 className="h-4 w-4 text-primary" />
        <h2 className="font-black">账号与数据源</h2>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {items.filter((item) => item.requires_user_login).map((item) => (
          <div key={item.provider} className="rounded-md border bg-white p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="font-black">{item.label}</p>
              <span className="rounded-md bg-muted px-2 py-1 text-xs font-bold">{item.status}</span>
            </div>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">{item.notes}</p>
            {item.requires_user_login ? (
              <button
                type="button"
                disabled={busy === item.provider}
                onClick={() => setStatus(item.provider, item.status === "connected" ? "needs_login" : "connected")}
                className="tn-button tn-button-secondary mt-3 w-full"
              >
                {busy === item.provider
                  ? "更新中"
                  : item.status === "connected"
                    ? "断开模拟连接"
                    : "标记为已授权"}
              </button>
            ) : null}
          </div>
        ))}
      </div>
      {error ? <p className="mt-3 text-sm font-semibold text-red-700">{error}</p> : null}
    </div>
  );
}
