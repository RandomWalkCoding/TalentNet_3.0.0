import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  description
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div className="tn-surface rounded-lg border-dashed p-8 text-center">
      <Icon className="mx-auto h-8 w-8 text-muted-foreground" />
      <h2 className="mt-3 font-black">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
        {description}
      </p>
    </div>
  );
}
