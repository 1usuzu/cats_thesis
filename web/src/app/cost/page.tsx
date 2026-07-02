"use client";

import { useI18n } from "@/lib/i18n";
import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function CostPage() {
  const { t } = useI18n();
  const { telemetryRecords } = useAppStore();
  
  const [selectedId, setSelectedId] = useState<string>(
    telemetryRecords.length > 0 ? telemetryRecords[telemetryRecords.length - 1].request_id : ""
  );

  const selectedRecord = telemetryRecords.find(r => r.request_id === selectedId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav_cost")}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t("cost_desc")}
        </p>
      </div>

      {!telemetryRecords.length ? (
        <div className="h-40 flex items-center justify-center border border-dashed rounded-lg text-sm text-muted-foreground">
          {t("no_telemetry")}
        </div>
      ) : (
        <div className="space-y-8">
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
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="text-sm font-medium text-muted-foreground">{t("cloud_exp_cost")}</div>
                <div className="mt-2 text-2xl font-bold text-foreground font-mono">
                  ${selectedRecord.cloud_expected_cost.toFixed(5)}
                </div>
              </div>
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="text-sm font-medium text-muted-foreground">{t("edge_exp_cost")}</div>
                <div className="mt-2 text-2xl font-bold text-foreground font-mono">
                  ${selectedRecord.edge_expected_cost.toFixed(5)}
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            <h3 className="font-semibold text-base">Historical Cost Overview</h3>
            <div className="rounded-md border border-border bg-card overflow-hidden">
              <Table>
                <TableHeader className="bg-secondary/50">
                  <TableRow>
                    <TableHead className="font-mono text-xs">timestamp</TableHead>
                    <TableHead className="font-mono text-xs">request_id</TableHead>
                    <TableHead className="font-mono text-xs">tag</TableHead>
                    <TableHead className="font-mono text-xs">selected_route</TableHead>
                    <TableHead className="font-mono text-xs text-right">cloud_expected_cost</TableHead>
                    <TableHead className="font-mono text-xs text-right">edge_expected_cost</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {telemetryRecords.map((r) => (
                    <TableRow key={r.request_id}>
                      <TableCell className="font-mono text-xs">{r.timestamp}</TableCell>
                      <TableCell className="font-mono text-xs">{r.request_id}</TableCell>
                      <TableCell className="font-mono text-xs">{r.tag}</TableCell>
                      <TableCell className="font-mono text-xs">
                        <span className={`px-1.5 py-0.5 rounded ${r.selected_route === 'EDGE' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-blue-500/10 text-blue-500'}`}>
                          {r.selected_route}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-right">${r.cloud_expected_cost.toFixed(5)}</TableCell>
                      <TableCell className="font-mono text-xs text-right">${r.edge_expected_cost.toFixed(5)}</TableCell>
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
