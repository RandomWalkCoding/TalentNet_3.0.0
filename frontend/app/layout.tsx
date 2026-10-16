import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/layout/app-shell";
import { cookies } from "next/headers";
import { getDemoSession } from "@/lib/api";

export const metadata: Metadata = {
  title: "TalentNet 竞对人才情报系统",
  description: "AI 辅助的竞对人才情报工作台"
};

export default async function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  const cookie = (await cookies()).toString();
  const session = await getDemoSession(cookie).catch(() => null);
  return (
    <html lang="zh-CN">
      <body>
        <AppShell session={session}>{children}</AppShell>
      </body>
    </html>
  );
}
