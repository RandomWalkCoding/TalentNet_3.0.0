import { getHealth } from "@/lib/api";

export async function HealthStatus() {
  const health = await getHealth();

  return (
    <div className="tn-surface rounded-lg p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-black text-primary">后端 API 状态</p>
          <h2 className="mt-2 text-2xl font-black">
            {health.ok ? "已连接" : "未连接"}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">FastAPI / SQLite / seed data</p>
        </div>
        <span
          className={
            health.ok
              ? "rounded-md bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-800"
              : "rounded-md bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-800"
          }
        >
          {health.ok ? "healthy" : "offline"}
        </span>
      </div>
      <pre className="mt-5 max-h-44 overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-5 text-slate-100 shadow-inner">
        {JSON.stringify(health.payload, null, 2)}
      </pre>
    </div>
  );
}
