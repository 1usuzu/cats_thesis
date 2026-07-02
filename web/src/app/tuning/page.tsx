"use client";

import { useI18n } from "@/lib/i18n";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav_tuning")}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Monitor Auto-Tuning heuristics and Canary validation in real-time.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Production Weights */}
        <div className="rounded-lg border border-border bg-card p-6">
          <h2 className="text-lg font-semibold mb-6">Production Weights (90%)</h2>
          <div className="space-y-6">
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">w_latency</div>
              <div className="text-xl font-bold font-mono">{((prod.w_latency as number) || 0).toFixed(3)}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">w_queue</div>
              <div className="text-xl font-bold font-mono">{((prod.w_queue as number) || 0).toFixed(3)}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">w_compute</div>
              <div className="text-xl font-bold font-mono">{((prod.w_compute as number) || 0).toFixed(3)}</div>
            </div>
          </div>
        </div>

        {/* Canary Weights */}
        <div className="rounded-lg border border-border bg-card p-6 relative overflow-hidden">
          {canaryActive ? (
            <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
              Canary Weights (10%)
              <span className="flex items-center gap-1.5 text-emerald-500 text-xs bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                ACTIVE
              </span>
            </h2>
          ) : (
            <h2 className="text-lg font-semibold mb-6 flex items-center gap-2 text-muted-foreground">
              Sandbox Weights
              <span className="flex items-center gap-1.5 text-muted-foreground text-xs bg-secondary px-2 py-0.5 rounded-full border border-border">
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground"></span>
                IDLE
              </span>
            </h2>
          )}
          
          <div className={`space-y-6 ${!canaryActive && "opacity-60"}`}>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">w_latency</div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono">{((sandbox.w_latency as number) || 0).toFixed(3)}</span>
                <span className="text-xs font-mono text-muted-foreground">
                  Δ {(((sandbox.w_latency as number) || 0) - ((prod.w_latency as number) || 0)).toFixed(3)}
                </span>
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">w_queue</div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono">{((sandbox.w_queue as number) || 0).toFixed(3)}</span>
                <span className="text-xs font-mono text-muted-foreground">
                  Δ {(((sandbox.w_queue as number) || 0) - ((prod.w_queue as number) || 0)).toFixed(3)}
                </span>
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">w_compute</div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono">{((sandbox.w_compute as number) || 0).toFixed(3)}</span>
                <span className="text-xs font-mono text-muted-foreground">
                  Δ {(((sandbox.w_compute as number) || 0) - ((prod.w_compute as number) || 0)).toFixed(3)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="border-t border-border pt-4 mt-6">
        <p className="text-sm text-foreground">
          <strong>LLM Strategic Assistance:</strong> Enabled (Triggered via <code className="bg-secondary px-1 py-0.5 rounded text-xs">tuning_agent.py</code>)
        </p>
      </div>
    </div>
  );
}
