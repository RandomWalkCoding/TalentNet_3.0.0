"use client";

import { useState } from "react";
import { type DemoSession, switchDemoUser } from "@/lib/api";

export function DemoUserSwitch({ session }: { session: DemoSession | null }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!session) return <span className="text-xs text-muted-foreground">后端未连接</span>;
  return <div className="grid gap-1">
    <label className="flex items-center gap-2 text-xs font-bold">
      本地演示用户
      <select className="tn-field" aria-label="本地演示用户" disabled={busy} value={session.user_id} onChange={async event => {
        setBusy(true); setError("");
        try { await switchDemoUser(event.target.value); window.location.reload(); }
        catch (err) { setError(err instanceof Error ? err.message : "切换失败"); setBusy(false); }
      }}>
        {session.users.map(user => <option key={user.id} value={user.id}>{user.name} · {user.role === "admin" ? "管理员" : "成员"}</option>)}
      </select>
    </label>
    {error && <p role="alert" className="text-xs text-red-700">{error}</p>}
  </div>;
}
