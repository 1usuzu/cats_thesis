"use client";

import { useI18n } from "@/lib/i18n";
import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DollarSign, Cloud, Cpu, TrendingUp, AlertTriangle, Calculator, Search } from "lucide-react";

export default function CostPage() {
  const { t } = useI18n();
  const { telemetryRecords } = useAppStore();
  
  const [selectedId, setSelectedId] = useState<string>(
    telemetryRecords.length > 0 ? telemetryRecords[telemetryRecords.length - 1].request_id : ""
  );

  const selectedRecord = telemetryRecords.find(r => r.request_id === selectedId);

  // Constants to match orchestrator/config.py for display
  const GEMINI_BASE_COST = 0.00015; 
  const EDGE_BASE_COST = 0.00002;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <DollarSign className="size-6 text-emerald-500" />
            {t("nav_cost")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("cost_desc") || "Phân tích rủi ro và ước tính chi phí định tuyến theo Google Gemini Pricing."}
          </p>
        </div>
        
        {telemetryRecords.length > 0 && (
          <div className="flex items-center gap-3 bg-secondary/30 p-1.5 rounded-lg border">
            <label className="text-xs font-semibold uppercase text-muted-foreground whitespace-nowrap pl-2 flex items-center gap-1">
              <Search className="size-3" /> {t("inspect_req")}
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
        <div className="h-40 flex items-center justify-center border border-dashed rounded-lg text-sm text-muted-foreground bg-secondary/10">
          {t("no_telemetry")}
        </div>
      ) : (
        <div className="space-y-6">
          
          {selectedRecord && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* Cloud Cost Card */}
              <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-5 shadow-sm relative overflow-hidden">
                <div className="absolute -right-4 -top-4 opacity-5 text-blue-500">
                  <Cloud className="size-32" />
                </div>
                <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 font-semibold mb-4">
                  <Cloud className="size-5" /> Cloud Expected Cost (Gemini Flash)
                </div>
                
                <div className="flex items-baseline gap-2 mb-6">
                  <span className="text-4xl font-bold text-foreground font-mono">
                    ${selectedRecord.cloud_expected_cost.toFixed(5)}
                  </span>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">/ 1K tokens</span>
                </div>

                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-center border-b border-blue-500/10 pb-2">
                    <span className="text-muted-foreground flex items-center gap-1.5"><Calculator className="size-3.5"/> Base API Cost</span>
                    <span className="font-mono font-medium">${GEMINI_BASE_COST.toFixed(5)}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-blue-500/10 pb-2">
                    <span className="text-muted-foreground flex items-center gap-1.5"><TrendingUp className="size-3.5 text-amber-500"/> Network Overhead & Retry Risk</span>
                    <span className="font-mono text-amber-600 dark:text-amber-400">
                      +${(selectedRecord.cloud_expected_cost - GEMINI_BASE_COST).toFixed(5)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Edge Cost Card */}
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 shadow-sm relative overflow-hidden">
                <div className="absolute -right-4 -top-4 opacity-5 text-emerald-500">
                  <Cpu className="size-32" />
                </div>
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold mb-4">
                  <Cpu className="size-5" /> Edge Expected Cost (Local GPU)
                </div>
                
                <div className="flex items-baseline gap-2 mb-6">
                  <span className="text-4xl font-bold text-foreground font-mono">
                    ${selectedRecord.edge_expected_cost.toFixed(5)}
                  </span>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">/ 1K tokens</span>
                </div>

                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-center border-b border-emerald-500/10 pb-2">
                    <span className="text-muted-foreground flex items-center gap-1.5"><Calculator className="size-3.5"/> Base Hardware Cost</span>
                    <span className="font-mono font-medium">${EDGE_BASE_COST.toFixed(5)}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-emerald-500/10 pb-2">
                    <span className="text-muted-foreground flex items-center gap-1.5"><AlertTriangle className="size-3.5 text-red-500"/> SLA Miss & Capacity Risk</span>
                    <span className="font-mono text-red-600 dark:text-red-400">
                      +${Math.max(0, selectedRecord.edge_expected_cost - EDGE_BASE_COST).toFixed(5)}
                    </span>
                  </div>
                </div>
              </div>

            </div>
          )}

          <div className="space-y-4 pt-4 border-t border-border/50">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <TrendingUp className="size-5 text-muted-foreground" /> Historical Cost Overview
            </h3>
            <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
              <Table>
                <TableHeader className="bg-secondary/50">
                  <TableRow>
                    <TableHead className="font-mono text-xs w-[180px]">Timestamp</TableHead>
                    <TableHead className="font-mono text-xs w-[120px]">Request ID</TableHead>
                    <TableHead className="font-mono text-xs">Tag</TableHead>
                    <TableHead className="font-mono text-xs w-[100px]">Route</TableHead>
                    <TableHead className="font-mono text-xs text-right text-blue-600/70 dark:text-blue-400/70">Cloud Cost</TableHead>
                    <TableHead className="font-mono text-xs text-right text-emerald-600/70 dark:text-emerald-400/70">Edge Cost</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {telemetryRecords.map((r) => (
                    <TableRow key={r.request_id} className="hover:bg-muted/50 transition-colors">
                      <TableCell className="font-mono text-[11px] text-muted-foreground">{r.timestamp}</TableCell>
                      <TableCell className="font-mono text-[11px]">{r.request_id.substring(0, 8)}...</TableCell>
                      <TableCell className="font-mono text-xs font-medium">
                        <span className="bg-secondary/80 px-1.5 py-0.5 rounded">{r.tag}</span>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        <span className={`px-2 py-0.5 rounded flex items-center gap-1.5 w-max ${r.selected_route === 'EDGE' ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20' : 'bg-blue-500/10 text-blue-600 border border-blue-500/20'}`}>
                          {r.selected_route === 'EDGE' ? <Cpu className="size-3"/> : <Cloud className="size-3"/>}
                          {r.selected_route}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-[11px] text-right font-medium text-blue-600 dark:text-blue-400">
                        ${r.cloud_expected_cost.toFixed(5)}
                      </TableCell>
                      <TableCell className="font-mono text-[11px] text-right font-medium text-emerald-600 dark:text-emerald-400">
                        ${r.edge_expected_cost.toFixed(5)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
