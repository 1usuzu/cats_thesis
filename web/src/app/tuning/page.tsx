"use client";

import { useI18n } from "@/lib/i18n";
import { useEffect, useState } from "react";
import { Loader2, SlidersHorizontal, ArrowRight, Bot, Zap, TestTube2, Scale } from "lucide-react";
import { useAppStore } from "@/lib/store";

export default function TuningPage() {
  const { t } = useI18n();
  const { apiKey } = useAppStore();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
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
          setData(await res.json());
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

  if (loading && !data) {
    return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-muted-foreground" /></div>;
  }

  const tuning = (data?.tuning as Record<string, unknown>) || {};
  const canaryActive = (tuning.canary_active as boolean) || false;
  const prod = (tuning.dynamic_weights as Record<string, unknown>) || {};
  const sandbox = (tuning.sandbox_weights as Record<string, unknown>) || {};

  const renderWeightBar = (label: string, prodValue: number, sandboxValue: number, showSandbox: boolean) => {
    const pValue = prodValue || 0;
    const sValue = sandboxValue || 0;
    const delta = sValue - pValue;
    
    return (
      <div className="space-y-2 mb-6">
        <div className="flex justify-between items-end">
          <div className="text-sm font-semibold text-muted-foreground flex items-center gap-1.5 uppercase tracking-wider">
            {label}
          </div>
          {showSandbox ? (
            <div className="flex items-center gap-3">
               <span className="text-xs font-mono text-muted-foreground strike line-through opacity-50">{pValue.toFixed(3)}</span>
               <span className="text-sm font-bold font-mono">{sValue.toFixed(3)}</span>
               <span className={`text-[10px] font-bold font-mono px-1.5 py-0.5 rounded ${delta > 0 ? 'bg-emerald-500/10 text-emerald-500' : delta < 0 ? 'bg-amber-500/10 text-amber-500' : 'bg-secondary text-muted-foreground'}`}>
                 {delta > 0 ? '+' : ''}{delta.toFixed(3)}
               </span>
            </div>
          ) : (
            <div className="text-sm font-bold font-mono">{pValue.toFixed(3)}</div>
          )}
        </div>
        <div className="h-2.5 w-full bg-secondary rounded-full overflow-hidden relative">
           <div className={`absolute top-0 left-0 h-full transition-all duration-700 ${showSandbox ? 'bg-muted-foreground/30' : 'bg-primary'}`} style={{ width: `${Math.min(100, Math.max(0, pValue * 100))}%` }}></div>
           {showSandbox && (
              <div className={`absolute top-0 left-0 h-full transition-all duration-700 opacity-80 ${delta > 0 ? 'bg-emerald-500' : delta < 0 ? 'bg-amber-500' : 'bg-primary'}`} style={{ width: `${Math.min(100, Math.max(0, sValue * 100))}%` }}></div>
           )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("nav_tuning")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("tuning_desc")}
          </p>
        </div>
        
        <div className="flex items-center gap-2 text-xs font-semibold bg-secondary/30 border px-3 py-1.5 rounded-lg text-indigo-600 dark:text-indigo-400">
          <Bot className="size-4" /> {t("tuning_ai_active")}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative">
        
        {/* Connection Arrow for Large Screens */}
        <div className="hidden lg:flex absolute inset-0 items-center justify-center pointer-events-none z-10">
          <div className="bg-background p-2 rounded-full border border-border shadow-sm text-muted-foreground">
             <ArrowRight className="size-5" />
          </div>
        </div>

        {/* Production Weights */}
        <div className="rounded-xl border border-primary/20 bg-card p-6 shadow-sm relative overflow-hidden">
          <div className="absolute -right-4 -top-4 opacity-5 text-primary">
            <Scale className="size-32" />
          </div>
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-lg font-bold flex items-center gap-2 text-primary">
               {t("tuning_prod_w")}
            </h2>
            <div className="bg-primary/10 text-primary text-xs font-bold px-2 py-1 rounded-md">90% {t("tuning_traffic")}</div>
          </div>
          
          <div className="space-y-2 relative z-10">
            {renderWeightBar("w_latency", prod.w_latency as number, 0, false)}
            {renderWeightBar("w_queue", prod.w_queue as number, 0, false)}
            {renderWeightBar("w_compute", prod.w_compute as number, 0, false)}
          </div>
        </div>

        {/* Canary Weights */}
        <div className={`rounded-xl border p-6 shadow-sm relative overflow-hidden transition-all duration-500 ${canaryActive ? 'border-amber-500/40 bg-amber-500/5' : 'border-border bg-card'}`}>
          <div className={`absolute -right-4 -top-4 opacity-5 ${canaryActive ? 'text-amber-500' : 'text-muted-foreground'}`}>
            <TestTube2 className="size-32" />
          </div>
          
          <div className="flex items-center justify-between mb-8 relative z-10">
            <h2 className={`text-lg font-bold flex items-center gap-2 ${canaryActive ? 'text-amber-600 dark:text-amber-500' : 'text-muted-foreground'}`}>
              {t("tuning_canary_w")}
            </h2>
            {canaryActive ? (
              <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-500 text-xs font-bold bg-amber-500/10 px-2 py-1 rounded-md border border-amber-500/20 shadow-sm animate-pulse">
                <Zap className="size-3" /> {t("tuning_testing")} 10% {t("tuning_traffic")}
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-muted-foreground text-xs font-bold bg-secondary px-2 py-1 rounded-md border border-border">
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground"></span> {t("tuning_idle")} (0% {t("tuning_traffic")})
              </span>
            )}
          </div>
          
          <div className={`space-y-2 relative z-10 transition-all duration-500 ${!canaryActive && "opacity-60 grayscale-[0.5]"}`}>
            {renderWeightBar("w_latency", prod.w_latency as number, sandbox.w_latency as number, true)}
            {renderWeightBar("w_queue", prod.w_queue as number, sandbox.w_queue as number, true)}
            {renderWeightBar("w_compute", prod.w_compute as number, sandbox.w_compute as number, true)}
          </div>
        </div>
      </div>
      
      <div className="border border-border bg-secondary/20 rounded-xl p-4 flex items-start gap-3 mt-6">
        <Bot className="size-5 text-muted-foreground mt-0.5" />
        <div className="text-sm text-foreground space-y-1">
          <p>
            <strong>{t("tuning_expl_title")}</strong> {t("tuning_expl_1")}
          </p>
          <p className="text-muted-foreground text-xs">
            {t("tuning_expl_2")}
          </p>
        </div>
      </div>
    </div>
  );
}
