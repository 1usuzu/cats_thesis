"use client";

import { useI18n } from "@/lib/i18n";
import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ArrowRight, Cloud, Server, ShieldCheck, ShieldAlert, Cpu, Tag, CheckCircle2, AlertTriangle, Calculator, Network } from "lucide-react";

export default function ExplainabilityPage() {
  const { t } = useI18n();
  const { telemetryRecords } = useAppStore();
  const [selectedId, setSelectedId] = useState<string>(
    telemetryRecords.length > 0 ? telemetryRecords[telemetryRecords.length - 1].request_id : ""
  );

  const selectedRecord = telemetryRecords.find(r => r.request_id === selectedId);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav_explain")}</h1>
        
        {telemetryRecords.length > 0 && (
          <div className="flex items-center gap-3 bg-secondary/30 p-1.5 rounded-lg border">
            <label className="text-xs font-semibold uppercase text-muted-foreground whitespace-nowrap pl-2">
              {t("inspect_req")}
            </label>
            <Select value={selectedId} onValueChange={(v) => setSelectedId(v as string)}>
              <SelectTrigger className="w-[300px] font-mono text-sm h-8 bg-background">
                <SelectValue placeholder={t("inspect_req")} />
              </SelectTrigger>
              <SelectContent>
              {telemetryRecords.map((r, i) => (
                <SelectItem key={i} value={r.request_id} className="font-mono text-sm">
                  {r.request_id.substring(0, 8)}... ({r.tag})
                </SelectItem>
              ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {!telemetryRecords.length ? (
        <div className="h-40 flex items-center justify-center border border-dashed rounded-lg text-sm text-muted-foreground">
          {t("no_telemetry")}
        </div>
      ) : (
        <div className="space-y-6">
          {selectedRecord && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Decision Summary */}
              <div className="lg:col-span-4 space-y-4 text-sm bg-card border rounded-xl p-5 shadow-sm">
                <h3 className="font-semibold text-lg border-b pb-2">{t("decision_summary")}</h3>
                
                <div className="bg-secondary/50 p-3 rounded-md italic font-mono text-xs">
                  &quot;{selectedRecord.prompt}&quot;
                </div>

                <div className="space-y-1">
                  <div><span className="font-semibold">{t("sel_route")}:</span> <code className="bg-secondary px-1 py-0.5 rounded text-xs">{selectedRecord.selected_route}</code></div>
                  <div><span className="font-semibold">{t("model")}:</span> <code className="bg-secondary px-1 py-0.5 rounded text-xs">{selectedRecord.selected_model}</code></div>
                  <div><span className="font-semibold">{t("score_diff")}:</span> {Math.abs(selectedRecord.cloud_score - selectedRecord.edge_score).toFixed(3)}</div>
                  <div className="pt-4 mt-4 border-t border-border">
                    <div className="bg-secondary/30 border rounded-lg p-3">
                      <div className="text-xs font-semibold uppercase text-muted-foreground mb-2 flex items-center gap-1">
                        <CheckCircle2 className="size-3" /> {t("optimal_route")}
                      </div>
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-md ${selectedRecord.edge_score >= selectedRecord.cloud_score ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-blue-500/20 text-blue-600 dark:text-blue-400'}`}>
                          {selectedRecord.edge_score >= selectedRecord.cloud_score ? <Cpu className="size-5" /> : <Cloud className="size-5" />}
                        </div>
                        <div>
                          <div className="font-bold text-base">
                            {selectedRecord.edge_score >= selectedRecord.cloud_score ? "EDGE NODE" : "CLOUD NODE"}
                          </div>
                          <div className={`text-xs font-medium mt-0.5 flex items-center gap-1 ${!selectedRecord.is_fallback ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                            {!selectedRecord.is_fallback ? <CheckCircle2 className="size-3" /> : <AlertTriangle className="size-3" />}
                            {!selectedRecord.is_fallback ? t("optimal_condition_met") : t("optimal_condition_failed")}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
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


              </div>

              {/* Right Column: Decision Pipeline */}
              <div className="lg:col-span-8 space-y-4">
                <h3 className="font-semibold text-lg">{t("decision_pipeline")}</h3>
                
                <div className="flex items-stretch justify-between gap-1.5 mt-2 w-full">
                  
                  {/* Step 1 */}
                  <div className="flex-1 border-2 border-primary/20 rounded-xl p-3 text-center text-xs relative bg-background shadow-sm flex flex-col items-center">
                    <div className="bg-primary/10 text-primary p-1.5 rounded-full mb-2">
                      <Tag className="size-4" />
                    </div>
                    <strong className="block mb-2 text-[11px] uppercase tracking-wider">1. {t("req_context")}</strong>
                    <div className="bg-secondary/50 px-1.5 py-1 rounded w-full text-foreground font-medium mb-1 truncate" title={selectedRecord.tag}>Tag: {selectedRecord.tag}</div>
                    <div className="text-muted-foreground text-[9px] truncate w-full">Strategy: {selectedRecord.strategy}</div>
                  </div>
                  
                  <div className="flex items-center text-muted-foreground/30 px-0.5"><ArrowRight className="size-4" /></div>

                  {/* Step 2 */}
                  <div className="flex-[1.2] border-2 border-primary/20 rounded-xl p-3 text-center text-xs relative bg-background shadow-sm flex flex-col items-center">
                    <div className="bg-primary/10 text-primary p-1.5 rounded-full mb-2">
                      <Calculator className="size-4" />
                    </div>
                    <strong className="block mb-2 text-[11px] uppercase tracking-wider">2. {t("scoring")}</strong>
                    
                    <div className="w-full space-y-3">
                      {/* Edge Score Bar */}
                      <div>
                        <div className="flex justify-between text-[10px] mb-1 font-semibold">
                          <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400"><Cpu className="size-3" /> EDGE</span>
                          <span>{selectedRecord.edge_score.toFixed(3)}</span>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-1.5 overflow-hidden flex">
                          <div className="bg-emerald-500 h-full transition-all duration-500" style={{ width: `${Math.min(100, Math.max(0, (selectedRecord.edge_score / Math.max(selectedRecord.edge_score, selectedRecord.cloud_score, 0.01)) * 100))}%` }}></div>
                        </div>
                      </div>
                      
                      {/* Cloud Score Bar */}
                      <div>
                        <div className="flex justify-between text-[10px] mb-1 font-semibold">
                          <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400"><Cloud className="size-3" /> CLOUD</span>
                          <span>{selectedRecord.cloud_score.toFixed(3)}</span>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-1.5 overflow-hidden flex">
                          <div className="bg-blue-500 h-full transition-all duration-500" style={{ width: `${Math.min(100, Math.max(0, (selectedRecord.cloud_score / Math.max(selectedRecord.edge_score, selectedRecord.cloud_score, 0.01)) * 100))}%` }}></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center text-muted-foreground/30 px-0.5"><ArrowRight className="size-4" /></div>

                  {/* Step 3 */}
                  <div className={`flex-1 border-2 rounded-xl p-3 text-center text-xs relative bg-background shadow-sm flex flex-col items-center ${selectedRecord.opa_status === 'enforced' && selectedRecord.opa_violations.length === 0 ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-red-500/50 bg-red-500/5'}`}>
                    <div className={`p-1.5 rounded-full mb-2 ${selectedRecord.opa_status === 'enforced' && selectedRecord.opa_violations.length === 0 ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-red-500/20 text-red-600 dark:text-red-400'}`}>
                      {selectedRecord.opa_status === 'enforced' && selectedRecord.opa_violations.length === 0 ? <ShieldCheck className="size-4" /> : <ShieldAlert className="size-4" />}
                    </div>
                    <strong className="block mb-2 text-[11px] uppercase tracking-wider">3. {t("opa_policy")}</strong>
                    <div className={`font-bold ${selectedRecord.opa_status === 'enforced' && selectedRecord.opa_violations.length === 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                      {selectedRecord.opa_status === 'enforced' && selectedRecord.opa_violations.length === 0 ? "SAFE" : "VIOLATION"}
                    </div>
                    <div className="text-muted-foreground text-[9px] mt-1">{selectedRecord.opa_violations.length} violations</div>
                  </div>

                  <div className="flex items-center text-muted-foreground/30 px-0.5"><ArrowRight className="size-4" /></div>

                  {/* Step 4 */}
                  <div className={`flex-1 border-2 rounded-xl p-3 text-center text-xs relative shadow-sm flex flex-col items-center justify-center ${selectedRecord.is_fallback ? 'border-amber-500 bg-amber-500/10' : 'border-blue-500 bg-blue-500/5'}`}>
                    <div className={`p-1.5 rounded-full mb-2 ${selectedRecord.is_fallback ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400' : 'bg-blue-500/20 text-blue-600 dark:text-blue-400'}`}>
                      <Network className="size-4" />
                    </div>
                    <strong className="block mb-2 text-[11px] uppercase tracking-wider">4. {t("output")}</strong>
                    <div className="font-bold text-sm text-foreground flex items-center justify-center gap-1 mt-1">
                      {selectedRecord.selected_route === "EDGE" ? <Cpu className="size-3.5" /> : <Cloud className="size-3.5" />}
                      {selectedRecord.selected_route}
                    </div>
                    {selectedRecord.is_fallback && <span className="bg-amber-500 text-white px-2 py-0.5 rounded text-[9px] font-bold mt-1.5 animate-pulse shadow-sm">FALLBACK</span>}
                    <div className="text-muted-foreground mt-2 font-mono text-[9px] bg-background/80 px-1 py-1 rounded w-full border border-border/50 truncate">Latency: {selectedRecord.latency_ms}ms</div>
                  </div>

                </div>

                <div className="pt-6 mt-4 border-t border-border/50">
                  <details className="group" open>
                    <summary className="font-semibold mb-2 block cursor-pointer hover:text-primary transition-colors select-none outline-none">
                      {t("telemetry_snap")} <span className="text-[10px] text-muted-foreground font-normal ml-1">(Click to collapse)</span>
                    </summary>
                    <pre className="bg-secondary/30 p-4 rounded-xl text-[11px] font-mono overflow-x-auto max-h-[30vh] overflow-y-auto border border-border/50 shadow-inner">
                      {JSON.stringify({
                        Tier1_State: selectedRecord.tier1_state,
                        Computed_Tag: selectedRecord.tag,
                        Hardware_Metrics: selectedRecord.telemetry_snapshot || "N/A"
                      }, null, 2)}
                    </pre>
                  </details>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
