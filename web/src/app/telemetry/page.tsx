"use client";

import { useI18n } from "@/lib/i18n";
import { Activity, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";

export default function TelemetryPage() {
  const { t } = useI18n();
  const { apiKey } = useAppStore();
  const [telemetryData, setTelemetryData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchTelemetry = async () => {
      try {
        const headers: Record<string, string> = apiKey ? { "X-API-Key": apiKey } : {};
        const res = await fetch("/api/telemetry", {
          headers
        });
        if (res.ok && mounted) {
          setTelemetryData(await res.json());
        }
      } catch (error) {
        console.error(error);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [apiKey]);

  const metrics = (telemetryData?.metrics as Record<string, unknown>) || {};
  const state = (telemetryData?.tier1_state as Record<string, unknown>) || {};
  
  const cloud_q = (metrics.cloud_gateway_inflight as number) || 0;
  const edge_q = (metrics.edge_gateway_inflight as number) || 0;
  const total_q = cloud_q + edge_q;
  const edge_cpu = (metrics.edge_cpu_util as number) || 0;
  const latency = (state.latency_ms as number) ?? ((metrics.edge_latency_ms as number) || 0);
  const proxy_val = Object.keys(state).length > 0 ? "ACTIVE" : "UNKNOWN";

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav_telemetry")}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t("health_desc")}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">{t("gw_queue")}</div>
          <div className="mt-2 text-xl font-bold text-foreground">
            {loading && !telemetryData ? <Loader2 className="size-4 animate-spin" /> : `${total_q} in-flight`}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">{t("edge_cpu")}</div>
          <div className="mt-2 text-xl font-bold text-foreground">
            {loading && !telemetryData ? <Loader2 className="size-4 animate-spin" /> : `${edge_cpu.toFixed(1)}%`}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">{t("net_latency")}</div>
          <div className="mt-2 text-xl font-bold text-foreground">
            {loading && !telemetryData ? <Loader2 className="size-4 animate-spin" /> : `${latency} ms`}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-sm font-medium text-muted-foreground">{t("proxy_status")}</div>
          <div className="mt-2 text-xl font-bold text-foreground">
            {loading && !telemetryData ? <Loader2 className="size-4 animate-spin" /> : proxy_val}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card">
        <div className="p-4 border-b border-border flex items-center justify-between bg-secondary/30">
           <h2 className="text-base font-semibold">Raw Telemetry Stream</h2>
           <div className="flex items-center gap-2 text-xs text-muted-foreground">
             <span className="relative flex h-2 w-2">
               <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
               <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
             </span>
             Live
           </div>
        </div>
        <div className="p-3 bg-background h-80 font-mono text-xs text-muted-foreground overflow-y-auto">
          {telemetryData ? (
             <pre>{JSON.stringify(telemetryData, null, 2)}</pre>
          ) : (
            <div className="h-full flex flex-col items-center justify-center">
               <Activity className="size-8 mb-2 animate-pulse text-border" />
               Waiting for telemetry signals...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
