"use client";

import { useI18n } from "@/lib/i18n";
import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";
import { Loader2, ShieldCheck, ShieldAlert, FileCode2, Wand2, CheckCircle2, XCircle, ArrowRight } from "lucide-react";

export default function PolicyPage() {
  const { t } = useI18n();
  const { apiKey } = useAppStore();
  const [statusData, setStatusData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const headers: Record<string, string> = apiKey ? { "X-API-Key": apiKey } : {};
      const res = await fetch("/api/policy/status", { headers });
      if (res.ok) {
        setStatusData(await res.json());
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    let mounted = true;
    const fetchWrapper = async () => {
      if (mounted) await fetchStatus();
    }
    fetchWrapper();
    const interval = setInterval(fetchWrapper, 3000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [fetchStatus]);

  const handleAction = async (endpoint: string, successMsg: string) => {
    setActionLoading(true);
    try {
      const headers: Record<string, string> = apiKey ? { "X-API-Key": apiKey } : {};
      const res = await fetch(`/api/policy/${endpoint}`, {
        method: "POST",
        headers
      });
      if (res.ok) {
        toast.success(successMsg);
        await fetchStatus();
      } else {
        const errorText = await res.text();
        toast.error(`Failed: ${errorText}`);
      }
    } catch (e: unknown) {
      toast.error(`Error: ${(e as Error).message}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && !statusData) {
    return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-muted-foreground" /></div>;
  }

  const activePolicy = (statusData?.active_policy as string) || "";
  const proposal = (statusData?.proposal as Record<string, unknown>) || {};
  const hasProposal = (proposal.has_proposal as boolean) || false;
  const valStatus = ((proposal.validation_results as Record<string, unknown>)?.status as string) || "NONE";
  const valDetails = ((proposal.validation_results as Record<string, unknown>)?.details as string) || "";

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <ShieldCheck className="size-6 text-emerald-500" />
            {t("nav_policy")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            LLM-proposed Rego policy modifications. Must be validated by Critic Agent before human approval.
          </p>
        </div>
        <Button 
          variant="default" 
          size="sm" 
          onClick={() => handleAction("trigger", "Triggered successfully. Wait a few seconds for Critic Agent to validate.")}
          disabled={actionLoading}
          className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-all"
        >
          {actionLoading ? <Loader2 className="size-4 animate-spin mr-2" /> : <Wand2 className="size-4 mr-2" />}
          Simulate Policy Proposal (LLM)
        </Button>
      </div>

      {hasProposal ? (
        <div className="space-y-6">
          {/* Critic Validation Banner */}
          <div className={`rounded-xl border p-5 flex flex-col sm:flex-row gap-4 items-start sm:items-center shadow-sm relative overflow-hidden ${
            valStatus === "PASSED" ? "bg-emerald-500/5 border-emerald-500/20" : 
            valStatus === "REJECTED" ? "bg-red-500/5 border-red-500/20" : 
            "bg-secondary/20 border-border"
          }`}>
            <div className={`p-3 rounded-full shrink-0 ${
              valStatus === "PASSED" ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400" : 
              valStatus === "REJECTED" ? "bg-red-500/20 text-red-600 dark:text-red-400" : 
              "bg-secondary text-muted-foreground"
            }`}>
              {valStatus === "PASSED" ? <CheckCircle2 className="size-6" /> : 
               valStatus === "REJECTED" ? <XCircle className="size-6" /> : 
               <Loader2 className="size-6 animate-spin" />}
            </div>
            
            <div className="flex-1">
              <h3 className={`font-semibold text-base ${
                valStatus === "PASSED" ? "text-emerald-600 dark:text-emerald-400" : 
                valStatus === "REJECTED" ? "text-red-600 dark:text-red-400" : 
                "text-foreground"
              }`}>
                Validation Status: {valStatus === "NONE" ? "VALIDATING..." : valStatus}
              </h3>
              {valDetails ? (
                <div className="text-sm text-muted-foreground mt-1 line-clamp-2" title={valDetails}>
                  {valDetails}
                </div>
              ) : (
                <div className="text-sm text-muted-foreground mt-1">Critic Agent is analyzing the proposed Rego policy for syntax errors and logical flaws...</div>
              )}
            </div>

            {valStatus === "PASSED" && (
              <div className="flex gap-2 shrink-0 w-full sm:w-auto">
                <Button 
                  onClick={() => handleAction("approve", "Policy Approved & Deployed!")}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white flex-1 sm:flex-none shadow-sm"
                  disabled={actionLoading}
                >
                  <ShieldCheck className="size-4 mr-1.5" /> Approve & Deploy
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => handleAction("reject", "Policy Rejected.")}
                  disabled={actionLoading}
                  className="border-red-500/30 text-red-600 hover:bg-red-500/10"
                >
                  Reject
                </Button>
              </div>
            )}

            {valStatus === "REJECTED" && (
              <Button 
                variant="outline"
                onClick={() => handleAction("reject", "Policy Dismissed.")}
                disabled={actionLoading}
                className="w-full sm:w-auto border-border shrink-0"
              >
                Dismiss Proposal
              </Button>
            )}
          </div>

          {/* Split View for Code */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 border border-border rounded-xl overflow-hidden shadow-sm relative">
            <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 bg-background border border-border p-2 rounded-full shadow-sm text-muted-foreground">
              <ArrowRight className="size-4" />
            </div>
            
            <div className="border-b lg:border-b-0 lg:border-r border-border bg-card flex flex-col">
              <div className="p-3 border-b border-border bg-secondary/30 flex items-center gap-2">
                <FileCode2 className="size-4 text-muted-foreground" />
                <h3 className="font-semibold text-sm">Active Rego Policy</h3>
              </div>
              <div className="p-4 h-[500px] overflow-y-auto">
                <pre className="text-[11px] font-mono leading-relaxed text-muted-foreground selection:bg-primary/20">{activePolicy}</pre>
              </div>
            </div>
            
            <div className="bg-card flex flex-col relative">
              <div className="p-3 border-b border-border bg-blue-500/5 flex items-center gap-2">
                <Wand2 className="size-4 text-blue-500" />
                <h3 className="font-semibold text-sm text-blue-600 dark:text-blue-400">Proposed Rego Policy</h3>
              </div>
              <div className="p-4 h-[500px] overflow-y-auto bg-blue-500/5">
                <pre className="text-[11px] font-mono leading-relaxed text-blue-900/80 dark:text-blue-200/80 selection:bg-blue-500/20">{proposal.proposed_policy as string}</pre>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="p-5 border border-emerald-500/20 bg-emerald-500/5 rounded-xl flex items-center gap-3 shadow-sm">
            <ShieldCheck className="size-6 text-emerald-600 dark:text-emerald-400" />
            <div>
              <div className="text-emerald-700 dark:text-emerald-400 font-semibold">No pending policy proposals.</div>
              <div className="text-emerald-600/80 dark:text-emerald-400/80 text-sm mt-0.5">The current Open Policy Agent (OPA) routing rules are stable.</div>
            </div>
          </div>
          <div className="border border-border rounded-xl overflow-hidden shadow-sm bg-card">
            <div className="p-3 border-b border-border bg-secondary/30 flex items-center gap-2">
              <FileCode2 className="size-4 text-muted-foreground" />
              <h3 className="font-semibold text-sm">Active Rego Policy (Deployed)</h3>
            </div>
            <div className="p-4 h-[600px] overflow-y-auto">
              <pre className="text-[11px] font-mono leading-relaxed text-foreground selection:bg-primary/20">{activePolicy}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
