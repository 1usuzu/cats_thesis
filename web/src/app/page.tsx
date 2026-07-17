"use client";

import { useI18n } from "@/lib/i18n";
import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Loader2, Server, Cpu, Cloud, ShieldCheck, LayoutDashboard, History, CheckCircle2, AlertCircle } from "lucide-react";

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

  const isGwHealthy = !!gwHealth;
  const isEdgeOnline = !!(gwHealth && (gwHealth?.checks as Record<string, unknown>)?.edge_node);
  const isCloudOnline = !!(gwHealth && (gwHealth?.checks as Record<string, unknown>)?.cloud_node);
  const isOpaEnforcing = !!telemetry;

  const sysStatusVal = isGwHealthy ? t("operational") : "OFFLINE";
  const gwMsg = isGwHealthy ? t("gw_healthy") : "Unreachable";
  const edgeStatusVal = isEdgeOnline ? t("online") : "OFFLINE";
  const cloudStatusVal = isCloudOnline ? t("online") : "OFFLINE";
  const opaStatusVal = isOpaEnforcing ? t("enforcing") : "UNKNOWN";

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("nav_overview")}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("overview_desc")}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* System Status */}
        <div className={`rounded-xl border p-5 shadow-sm transition-colors duration-500 relative overflow-hidden ${isGwHealthy ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
          <div className={`absolute -right-2 -top-2 opacity-5 ${isGwHealthy ? 'text-emerald-500' : 'text-red-500'}`}><Server className="size-24"/></div>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-3">
             <Server className="size-4" /> {t("sys_status")}
          </div>
          <div className={`text-2xl font-bold font-mono tracking-tight ${isGwHealthy ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
            {loading && !gwHealth ? <Loader2 className="size-5 animate-spin mt-1" /> : sysStatusVal}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1 font-medium">{gwMsg}</div>
        </div>

        {/* Edge Status */}
        <div className={`rounded-xl border p-5 shadow-sm transition-colors duration-500 relative overflow-hidden ${isEdgeOnline ? 'bg-blue-500/10 border-blue-500/30' : 'bg-secondary border-border'}`}>
          <div className={`absolute -right-2 -top-2 opacity-5 ${isEdgeOnline ? 'text-blue-500' : 'text-muted-foreground'}`}><Cpu className="size-24"/></div>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-3">
             <Cpu className="size-4" /> {t("edge_status")}
          </div>
          <div className={`text-2xl font-bold font-mono tracking-tight ${isEdgeOnline ? 'text-blue-600 dark:text-blue-400' : 'text-muted-foreground'}`}>
            {loading && !gwHealth ? <Loader2 className="size-5 animate-spin mt-1" /> : edgeStatusVal}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1 font-medium">Local GPU (Phi 3)</div>
        </div>

        {/* Cloud Status */}
        <div className={`rounded-xl border p-5 shadow-sm transition-colors duration-500 relative overflow-hidden ${isCloudOnline ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-secondary border-border'}`}>
          <div className={`absolute -right-2 -top-2 opacity-5 ${isCloudOnline ? 'text-indigo-500' : 'text-muted-foreground'}`}><Cloud className="size-24"/></div>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-3">
             <Cloud className="size-4" /> {t("cloud_status")}
          </div>
          <div className={`text-2xl font-bold font-mono tracking-tight ${isCloudOnline ? 'text-indigo-600 dark:text-indigo-400' : 'text-muted-foreground'}`}>
            {loading && !gwHealth ? <Loader2 className="size-5 animate-spin mt-1" /> : cloudStatusVal}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1 font-medium">Google Gemini API</div>
        </div>

        {/* OPA Safety */}
        <div className={`rounded-xl border p-5 shadow-sm transition-colors duration-500 relative overflow-hidden ${isOpaEnforcing ? 'bg-amber-500/10 border-amber-500/30' : 'bg-secondary border-border'}`}>
          <div className={`absolute -right-2 -top-2 opacity-5 ${isOpaEnforcing ? 'text-amber-500' : 'text-muted-foreground'}`}><ShieldCheck className="size-24"/></div>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-3">
             <ShieldCheck className="size-4" /> {t("opa_safety")}
          </div>
          <div className={`text-2xl font-bold font-mono tracking-tight ${isOpaEnforcing ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground'}`}>
            {loading && !telemetry ? <Loader2 className="size-5 animate-spin mt-1" /> : opaStatusVal}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1 font-medium">Rego Policies</div>
        </div>
      </div>

      <div className="space-y-4 pt-4 border-t border-border/50">
        <h3 className="font-semibold text-lg flex items-center gap-2">
          <History className="size-5 text-muted-foreground" /> {t("recent_reqs")}
        </h3>
        {!telemetryRecords.length ? (
          <div className="h-40 flex flex-col items-center justify-center border border-dashed rounded-xl bg-secondary/20 text-sm text-muted-foreground">
            <LayoutDashboard className="size-8 mb-3 opacity-20" />
            {t("no_telemetry")}
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
            <Table>
              <TableHeader className="bg-secondary/50">
                <TableRow>
                  <TableHead className="font-mono text-xs w-[180px]">Timestamp</TableHead>
                  <TableHead className="font-mono text-xs w-[120px]">Request ID</TableHead>
                  <TableHead className="font-mono text-xs w-[250px] lg:w-[400px]">Prompt</TableHead>
                  <TableHead className="font-mono text-xs">Tag</TableHead>
                  <TableHead className="font-mono text-xs">Route</TableHead>
                  <TableHead className="font-mono text-xs text-right">Latency</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...telemetryRecords].reverse().slice(0, 10).map((r) => (
                  <TableRow key={r.request_id} className="group hover:bg-secondary/20">
                    <TableCell className="font-mono text-[11px] text-muted-foreground whitespace-nowrap">{r.timestamp}</TableCell>
                    <TableCell className="font-mono text-[11px]">{r.request_id}</TableCell>
                    <TableCell className="font-mono text-[11px] truncate max-w-[250px] lg:max-w-[400px] text-foreground/80 group-hover:text-foreground transition-colors" title={r.prompt}>
                      {r.prompt}
                    </TableCell>
                    <TableCell className="font-mono text-[11px]">
                      <span className="px-2 py-0.5 rounded-full bg-secondary text-muted-foreground border border-border">{r.tag}</span>
                    </TableCell>
                    <TableCell className="font-mono text-[11px]">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded-md font-bold text-[10px] flex items-center gap-1 w-fit ${r.selected_route === 'EDGE' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' : 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20'}`}>
                          {r.selected_route === 'EDGE' ? <Cpu className="size-3" /> : <Cloud className="size-3" />}
                          {r.selected_route}
                        </span>
                        {r.is_fallback && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/10 text-amber-600 border border-amber-500/20 flex items-center gap-1" title="Safety Fallback Triggered">
                            <AlertCircle className="size-2.5" /> FALLBACK
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-[11px] text-right font-medium">{r.latency_ms}ms</TableCell>
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
