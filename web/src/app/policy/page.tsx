"use client";

import { useI18n } from "@/lib/i18n";
import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

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
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("nav_policy")}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            LLM-proposed Rego policy modifications. Must be validated by Critic Agent before human approval.
          </p>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => handleAction("trigger", "Triggered successfully. Wait a few seconds for Critic Agent to validate.")}
          disabled={actionLoading}
        >
          {actionLoading ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
          Trigger Policy Proposal (Simulate LLM)
        </Button>
      </div>

      {hasProposal ? (
        <div className="space-y-4">
          <div className="rounded-md border border-border bg-card p-4">
            <h3 className="font-semibold text-sm mb-2">Proposal Validation Status: {valStatus}</h3>
            {valDetails && (
              <pre className="bg-secondary p-3 rounded text-xs font-mono whitespace-pre-wrap mt-2 text-muted-foreground">
                {valDetails}
              </pre>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-2">
              <h3 className="font-semibold text-sm">Active Rego Policy</h3>
              <div className="rounded-md border border-border bg-card h-80 overflow-y-auto p-4">
                <pre className="text-[11px] font-mono">{activePolicy}</pre>
              </div>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold text-sm text-blue-500">Proposed Rego Policy</h3>
              <div className="rounded-md border border-border bg-card h-80 overflow-y-auto p-4">
                <pre className="text-[11px] font-mono">{proposal.proposed_policy as string}</pre>
              </div>
            </div>
          </div>

          {valStatus === "PASSED" && (
            <div className="flex gap-4 p-4 border border-emerald-500/20 bg-emerald-500/5 rounded-lg items-center justify-between">
              <div className="text-sm text-emerald-600 font-medium">
                Critic Agent has validated this policy. Ready for deployment.
              </div>
              <div className="flex gap-2">
                <Button 
                  onClick={() => handleAction("approve", "Policy Approved & Deployed!")}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  disabled={actionLoading}
                >
                  Approve & Deploy to OPA
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => handleAction("reject", "Policy Rejected.")}
                  disabled={actionLoading}
                >
                  Reject
                </Button>
              </div>
            </div>
          )}

          {valStatus === "REJECTED" && (
            <div className="flex gap-4 p-4 border border-red-500/20 bg-red-500/5 rounded-lg items-center justify-between">
              <div className="text-sm text-red-600 font-medium">
                Critic Agent rejected this policy. You cannot deploy it.
              </div>
              <Button 
                variant="outline"
                onClick={() => handleAction("reject", "Policy Dismissed.")}
                disabled={actionLoading}
              >
                Dismiss
              </Button>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-4 border border-emerald-500/20 bg-emerald-500/5 rounded-lg text-emerald-600 font-medium text-sm">
            No pending policy proposals.
          </div>
          <div className="space-y-2">
            <h3 className="font-semibold text-sm">Active Rego Policy</h3>
            <div className="rounded-md border border-border bg-card h-96 overflow-y-auto p-4">
              <pre className="text-[11px] font-mono">{activePolicy}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
