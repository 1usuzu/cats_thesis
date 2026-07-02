"use client";

import { useI18n } from "@/lib/i18n";
import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Loader2 } from "lucide-react";

export default function Home() {
  const { t } = useI18n();
  const { apiKey, telemetryRecords } = useAppStore();
  
  const [gwHealth, setGwHealth] = useState<Record<string, unknown> | null>(null);
  const [telemetry, setTelemetry] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchData = async () => {
      try {
        const headers: Record<string, string> = apiKey ? { "X-API-Key": apiKey } : {};
        const [resHealth, resTel] = await Promise.all([
          fetch("/api/health", { headers }),
          fetch("/api/telemetry", { headers })
        ]);
        
        if (mounted) {
          if (resHealth.ok) setGwHealth(await resHealth.json());
          if (resTel.ok) setTelemetry(await resTel.json());
          setLoading(false);
        }
      } catch (error) {
        console.error(error);
        if (mounted) setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [apiKey]);

  const sysStatusVal = gwHealth ? t("operational") : "OFFLINE";
  const gwMsg = gwHealth ? t("gw_healthy") : "Unreachable";
  const edgeStatusVal = (gwHealth && (gwHealth?.checks as Record<string, unknown>)?.edge_node) ? t("online") : "OFFLINE";
  const cloudStatusVal = (gwHealth && (gwHealth?.checks as Record<string, unknown>)?.cloud_node) ? t("online") : "OFFLINE";
  const opaStatusVal = telemetry ? t("enforcing") : "UNKNOWN";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav_overview")}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t("overview_desc")}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">{t("sys_status")}</div>
          <div className="mt-2 text-xl font-bold text-foreground">
            {loading && !gwHealth ? <Loader2 className="size-4 animate-spin" /> : sysStatusVal}
          </div>
          <div className="text-xs text-muted-foreground mt-1">{gwMsg}</div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">{t("edge_status")}</div>
          <div className="mt-2 text-xl font-bold text-foreground">
            {loading && !gwHealth ? <Loader2 className="size-4 animate-spin" /> : edgeStatusVal}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">{t("cloud_status")}</div>
          <div className="mt-2 text-xl font-bold text-foreground">
            {loading && !gwHealth ? <Loader2 className="size-4 animate-spin" /> : cloudStatusVal}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">{t("opa_safety")}</div>
          <div className="mt-2 text-xl font-bold text-foreground">
            {loading && !telemetry ? <Loader2 className="size-4 animate-spin" /> : opaStatusVal}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="font-semibold text-base">{t("recent_reqs")}</h3>
        {!telemetryRecords.length ? (
          <div className="h-32 flex items-center justify-center border border-dashed rounded-lg text-sm text-muted-foreground">
            {t("no_telemetry")}
          </div>
        ) : (
          <div className="rounded-md border border-border bg-card overflow-hidden">
            <Table>
              <TableHeader className="bg-secondary/50">
                <TableRow>
                  <TableHead className="font-mono text-xs">timestamp</TableHead>
                  <TableHead className="font-mono text-xs">request_id</TableHead>
                  <TableHead className="font-mono text-xs w-[300px]">prompt</TableHead>
                  <TableHead className="font-mono text-xs">tag</TableHead>
                  <TableHead className="font-mono text-xs">selected_route</TableHead>
                  <TableHead className="font-mono text-xs">is_fallback</TableHead>
                  <TableHead className="font-mono text-xs text-right">latency_ms</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...telemetryRecords].reverse().map((r) => (
                  <TableRow key={r.request_id}>
                    <TableCell className="font-mono text-xs whitespace-nowrap">{r.timestamp}</TableCell>
                    <TableCell className="font-mono text-xs">{r.request_id}</TableCell>
                    <TableCell className="font-mono text-xs truncate max-w-[300px]" title={r.prompt}>
                      {r.prompt}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{r.tag}</TableCell>
                    <TableCell className="font-mono text-xs">
                      <span className={`px-1.5 py-0.5 rounded ${r.selected_route === 'EDGE' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-blue-500/10 text-blue-500'}`}>
                        {r.selected_route}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{r.is_fallback ? "True" : "False"}</TableCell>
                    <TableCell className="font-mono text-xs text-right">{r.latency_ms}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}
