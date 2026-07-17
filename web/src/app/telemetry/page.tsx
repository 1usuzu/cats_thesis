"use client";

import { useI18n } from "@/lib/i18n";
import { Activity, Loader2, PauseCircle, PlayCircle, Terminal, Cpu, Clock, Network, AlertCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";

export default function TelemetryPage() {
  const { t } = useI18n();
  const { apiKey } = useAppStore();
  const [telemetryData, setTelemetryData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    let mounted = true;
    const fetchTelemetry = async () => {
      if (isPaused) return;
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

    if (!isPaused) {
      fetchTelemetry();
    }
    const interval = setInterval(fetchTelemetry, 3000);
    
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [apiKey, isPaused]);

  const metrics = (telemetryData?.metrics as Record<string, unknown>) || {};
  const state = (telemetryData?.tier1_state as Record<string, unknown>) || {};
  
  const cloud_q = (metrics.cloud_gateway_inflight as number) || 0;
  const edge_q = (metrics.edge_gateway_inflight as number) || 0;
  const total_q = cloud_q + edge_q;
  const edge_cpu = (metrics.edge_cpu_util as number) || 0;
  const latency = (state.latency_ms as number) ?? ((metrics.edge_latency_ms as number) || 0);
  const proxy_val = Object.keys(state).length > 0 ? "ACTIVE" : "UNKNOWN";

  const isHighLatency = latency > 150;
  const isHighCpu = edge_cpu > 80;
  const isHighQueue = total_q > 20;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("nav_telemetry")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("health_desc")}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Queue Box */}
        <div className={`rounded-xl border p-4 shadow-sm transition-colors duration-500 relative overflow-hidden ${isHighQueue ? 'bg-amber-500/10 border-amber-500/30' : 'bg-card border-border'}`}>
          <div className={`absolute -right-2 -top-2 opacity-5 ${isHighQueue ? 'text-amber-500' : 'text-muted-foreground'}`}><Activity className="size-16"/></div>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-2">
             <Activity className="size-4" /> Gateway Queue
          </div>
          <div className={`text-2xl font-bold font-mono tracking-tight ${isHighQueue ? 'text-amber-600 dark:text-amber-400' : 'text-foreground'}`}>
            {loading && !telemetryData ? <Loader2 className="size-5 animate-spin mt-1" /> : `${total_q}`}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1 font-medium">{t("tel_req_in_flight")}</div>
        </div>

        {/* Edge CPU Box */}
        <div className={`rounded-xl border p-4 shadow-sm transition-colors duration-500 relative overflow-hidden ${isHighCpu ? 'bg-red-500/10 border-red-500/30' : 'bg-card border-border'}`}>
          <div className={`absolute -right-2 -top-2 opacity-5 ${isHighCpu ? 'text-red-500' : 'text-muted-foreground'}`}><Cpu className="size-16"/></div>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-2">
             <Cpu className="size-4" /> {t("edge_cpu")}
          </div>
          <div className={`text-2xl font-bold font-mono tracking-tight ${isHighCpu ? 'text-red-600 dark:text-red-400' : 'text-foreground'}`}>
            {loading && !telemetryData ? <Loader2 className="size-5 animate-spin mt-1" /> : `${edge_cpu.toFixed(1)}%`}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1 font-medium">{t("tel_cpu_load")}</div>
        </div>

        {/* Latency Box */}
        <div className={`rounded-xl border p-4 shadow-sm transition-colors duration-500 relative overflow-hidden ${isHighLatency ? 'bg-amber-500/10 border-amber-500/30' : 'bg-card border-border'}`}>
          <div className={`absolute -right-2 -top-2 opacity-5 ${isHighLatency ? 'text-amber-500' : 'text-muted-foreground'}`}><Clock className="size-16"/></div>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-2">
             <Clock className="size-4" /> {t("net_latency")}
          </div>
          <div className={`text-2xl font-bold font-mono tracking-tight ${isHighLatency ? 'text-amber-600 dark:text-amber-400' : 'text-foreground'}`}>
            {loading && !telemetryData ? <Loader2 className="size-5 animate-spin mt-1" /> : `${latency}ms`}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1 font-medium">{t("tel_net_delay")}</div>
        </div>

        {/* Proxy Box */}
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 shadow-sm relative overflow-hidden">
          <div className="absolute -right-2 -top-2 opacity-5 text-emerald-500"><Network className="size-16"/></div>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-2">
             <Network className="size-4" /> {t("proxy_status")}
          </div>
          <div className="text-2xl font-bold font-mono tracking-tight text-emerald-600 dark:text-emerald-400">
            {loading && !telemetryData ? <Loader2 className="size-5 animate-spin mt-1" /> : proxy_val}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1 font-medium">{t("tel_proxy_cp")}</div>
        </div>
      </div>

      <div className="rounded-xl border border-border shadow-sm overflow-hidden flex flex-col bg-card">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-secondary/30 sticky top-0">
           <h2 className="text-sm font-semibold flex items-center gap-2 text-foreground">
             <Terminal className="size-4 text-muted-foreground" />
             {t("tel_raw")}
           </h2>
           
           <div className="flex items-center gap-4">
             {isPaused ? (
               <button 
                 onClick={() => setIsPaused(false)}
                 className="flex items-center gap-1.5 text-xs text-amber-500 hover:text-amber-600 dark:hover:text-amber-400 transition-colors font-medium bg-amber-500/10 px-2 py-1 rounded"
               >
                 <PlayCircle className="size-3.5" /> {t("tel_paused")}
               </button>
             ) : (
               <button 
                 onClick={() => setIsPaused(true)}
                 className="flex items-center gap-1.5 text-xs text-emerald-500 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors font-medium bg-emerald-500/10 px-2 py-1 rounded"
               >
                 <span className="relative flex h-2 w-2 mr-0.5">
                   <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                   <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                 </span>
                 {t("tel_live")}
               </button>
             )}
           </div>
        </div>
        
        <div className="p-4 max-h-[40vh] overflow-y-auto font-mono text-[11px] md:text-xs selection:bg-primary/20">
          {telemetryData ? (
             <pre className="text-muted-foreground">{JSON.stringify(telemetryData, null, 2)}</pre>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground py-10">
               <Activity className="size-8 mb-3 animate-pulse opacity-50" />
               {t("tel_waiting")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
