"use client";

import { useI18n } from "@/lib/i18n";
import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ArrowRight } from "lucide-react";

export default function ExplainabilityPage() {
  const { t } = useI18n();
  const { telemetryRecords } = useAppStore();
  const [selectedId, setSelectedId] = useState<string>(
    telemetryRecords.length > 0 ? telemetryRecords[telemetryRecords.length - 1].request_id : ""
  );

  const selectedRecord = telemetryRecords.find(r => r.request_id === selectedId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav_explain")}</h1>
      </div>

      {!telemetryRecords.length ? (
        <div className="h-40 flex items-center justify-center border border-dashed rounded-lg text-sm text-muted-foreground">
          {t("no_telemetry")}
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="col-span-1">
              <label className="text-xs font-semibold uppercase text-muted-foreground mb-2 block">
                {t("inspect_req")}
              </label>
              <Select value={selectedId} onValueChange={(v) => setSelectedId(v as string)}>
                <SelectTrigger className="w-full font-mono text-sm h-9">
                  <SelectValue placeholder={t("inspect_req")} />
                </SelectTrigger>
                <SelectContent className="min-w-[400px]">
                {telemetryRecords.map((r, i) => (
                  <SelectItem key={i} value={r.request_id} className="font-mono text-sm pr-8">
                    {r.request_id} ({r.tag}) - {r.timestamp}
                  </SelectItem>
                ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {selectedRecord && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Left Column: Decision Summary */}
              <div className="col-span-1 space-y-4 text-sm">
                <h3 className="font-semibold text-base">{t("decision_summary")}</h3>
                
                <div className="bg-secondary/50 p-3 rounded-md italic font-mono text-xs">
                  &quot;{selectedRecord.prompt}&quot;
                </div>

                <div className="space-y-1">
                  <div><span className="font-semibold">{t("sel_route")}:</span> <code className="bg-secondary px-1 py-0.5 rounded text-xs">{selectedRecord.selected_route}</code></div>
                  <div><span className="font-semibold">{t("model")}:</span> <code className="bg-secondary px-1 py-0.5 rounded text-xs">{selectedRecord.selected_model}</code></div>
                  <div><span className="font-semibold">{t("score_diff")}:</span> {Math.abs(selectedRecord.cloud_score - selectedRecord.edge_score).toFixed(3)}</div>
                </div>

                <div>
                  <span className="font-semibold">{t("primary_reason")}:</span><br/>
                  <span className="text-muted-foreground font-medium text-amber-600 dark:text-amber-400">
                    {selectedRecord.primary_reason || (selectedRecord.selected_route === "EDGE" ? t("reason_edge") : t("reason_cloud"))}
                  </span>
                </div>

                <div className="pt-2 border-t border-border">
                  <span className="font-semibold">{t("alt_route")}</span><br/>
                  <div className="text-muted-foreground mt-1">
                    Fallback: <span className="font-semibold">{selectedRecord.selected_route === "EDGE" ? "CLOUD" : "EDGE"}</span><br/>
                    Score: {(selectedRecord.selected_route === "EDGE" ? selectedRecord.cloud_score : selectedRecord.edge_score).toFixed(3)}
                  </div>
                </div>

                <div className="pt-2 border-t border-border">
                  <span className="font-semibold mb-2 block">{t("telemetry_snap")}</span>
                  <pre className="bg-secondary p-2 rounded-md text-[10px] font-mono overflow-x-auto">
                    {JSON.stringify({
                      Tier1_State: selectedRecord.tier1_state,
                      Computed_Tag: selectedRecord.tag,
                      Hardware_Metrics: selectedRecord.telemetry_snapshot || "N/A"
                    }, null, 2)}
                  </pre>
                </div>
              </div>

              {/* Right Column: Decision Pipeline */}
              <div className="col-span-2 space-y-4">
                <h3 className="font-semibold text-base">{t("decision_pipeline")}</h3>
                
                <div className="flex items-stretch justify-between gap-2 mt-4 overflow-x-auto pb-4">
                  
                  {/* Step 1 */}
                  <div className="flex-1 min-w-[140px] border-2 border-blue-500 rounded-md p-3 text-center text-xs relative bg-background">
                    <strong className="block mb-2 text-sm">1. {t("req_context")}</strong>
                    <div className="text-muted-foreground">Tag: {selectedRecord.tag}</div>
                    <div className="text-muted-foreground">Strategy: {selectedRecord.strategy}</div>
                  </div>
                  
                  <div className="flex items-center text-muted-foreground/50 px-1"><ArrowRight className="size-4" /></div>

                  {/* Step 2 */}
                  <div className="flex-1 min-w-[180px] border-2 border-blue-500 rounded-md p-3 text-center text-xs relative bg-background">
                    <strong className="block mb-2 text-sm">2. {t("scoring")}</strong>
                    <div className="mb-2 pb-2 border-b border-border/50">
                      <div className="text-[10px] font-semibold text-muted-foreground mb-1">BASE SCORE (Raw)</div>
                      <div className="text-muted-foreground flex justify-between px-2"><span>Edge: {(selectedRecord.edge_base_score || 0).toFixed(3)}</span> <span>Cloud: {(selectedRecord.cloud_base_score || 0).toFixed(3)}</span></div>
                    </div>
                    <div>
                      <div className="text-[10px] font-semibold text-muted-foreground mb-1">FINAL SCORE (w/ Tier 1)</div>
                      <div className="text-foreground font-medium flex justify-between px-2"><span>Edge: {selectedRecord.edge_score.toFixed(3)}</span> <span>Cloud: {selectedRecord.cloud_score.toFixed(3)}</span></div>
                    </div>
                  </div>

                  <div className="flex items-center text-muted-foreground/50 px-1"><ArrowRight className="size-4" /></div>

                  {/* Step 3 */}
                  <div className={`flex-1 min-w-[140px] border-2 rounded-md p-3 text-center text-xs relative bg-background ${selectedRecord.opa_status === 'enforced' && selectedRecord.opa_violations.length === 0 ? 'border-emerald-500' : 'border-red-500'}`}>
                    <strong className="block mb-2 text-sm">3. {t("opa_policy")}</strong>
                    <div className="text-muted-foreground">Status: {selectedRecord.opa_status.toUpperCase()}</div>
                    <div className="text-muted-foreground">Violations: {selectedRecord.opa_violations.length}</div>
                  </div>

                  <div className="flex items-center text-muted-foreground/50 px-1"><ArrowRight className="size-4" /></div>

                  {/* Step 4 */}
                  <div className={`flex-1 min-w-[140px] border-2 rounded-md p-3 text-center text-xs relative ${selectedRecord.is_fallback ? 'border-amber-500 bg-amber-500/10' : 'border-blue-500 bg-blue-500/10'}`}>
                    <strong className="block mb-2 text-sm">4. {t("output")}</strong>
                    <div className="font-semibold text-foreground">
                      Route: {selectedRecord.selected_route}
                      {selectedRecord.is_fallback && <span className="text-amber-500 ml-1">(FALLBACK)</span>}
                    </div>
                    <div className="text-muted-foreground mt-1">Latency: {selectedRecord.latency_ms}ms</div>
                  </div>

                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
