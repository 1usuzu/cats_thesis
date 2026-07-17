"use client";

import Link from "next/link";
import { LayoutDashboard, Network, TerminalSquare, DollarSign, SlidersHorizontal, ShieldCheck, Activity } from "lucide-react";
import { useI18n } from "@/lib/i18n";

export function Sidebar() {
  const { t } = useI18n();

  const navItems = [
    { name: t("nav_overview"), href: "/", icon: LayoutDashboard },
    { name: t("nav_console"), href: "/console", icon: TerminalSquare },
    { name: t("nav_explain"), href: "/explainability", icon: Network },
    { name: t("nav_cost"), href: "/cost", icon: DollarSign },
    { name: t("nav_tuning"), href: "/tuning", icon: SlidersHorizontal },
    { name: t("nav_policy"), href: "/policy", icon: ShieldCheck },
    { name: t("nav_telemetry"), href: "/telemetry", icon: Activity },
  ];

  return (
    <aside className="w-64 border-r border-border bg-card flex flex-col h-full shrink-0">
      <Link href="/" className="h-14 border-b border-border flex items-center gap-3 px-4 hover:bg-secondary/50 transition-colors">
        <span className="font-semibold text-sm truncate">CATS Control Plane</span>
      </Link>
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-secondary rounded-md transition-colors font-medium"
                >
                  <Icon className="size-4" />
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="p-4 border-t border-border flex items-center gap-2">
        <div className="size-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
        <div className="text-xs text-muted-foreground font-mono">
          {t("system_online")}
        </div>
      </div>
    </aside>
  );
}
