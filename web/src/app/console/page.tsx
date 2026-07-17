"use client";

import { useI18n } from "@/lib/i18n";
import { useState, useRef, useEffect } from "react";
import { Loader2, Send, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";
export default function ConsolePage() {
  const { t } = useI18n();
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [strategy, setStrategy] = useState("PROPOSED");
  const scrollRef = useRef<HTMLDivElement>(null);

  const { 
    apiKey, 
    requestTag, 
    messages, 
    addMessage, 
    clearMessages,
    telemetryRecords,
    addTelemetryRecord,
    clearTelemetryRecords
  } = useAppStore();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleClear = () => {
    clearMessages();
    clearTelemetryRecords();
    toast.success(t("clear_history") + " successful");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    const userPrompt = prompt.trim();
    setPrompt("");
    addMessage({ role: "user", content: userPrompt });

    setLoading(true);
    const startT = performance.now();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "X-API-Key": apiKey
        },
        body: JSON.stringify({
          prompt: userPrompt,
          request_tag: requestTag,
          strategy: strategy
        }),
      });

      if (res.status === 401 || res.status === 403) {
        toast.error("Invalid API Key. Please update your API Key.");
        addMessage({ role: "assistant", content: `**${t("api_err")} ${res.status}:** Unauthorized` });
        return;
      }

      const duration_ms = Math.round(performance.now() - startT);

      if (res.ok) {
        const data = await res.json();
        const content = data?.data?.response || t("no_resp");
        addMessage({ role: "assistant", content });

        // Add telemetry record matching Python dashboard logic
        const api_resp = data?.data || {};
        const route_info = api_resp?.route || {};
        const meta = data?.meta || {};
        const analysis = meta?.routing_analysis || {};
        const final_scores = analysis?.final_scores || {};
        const cats_scores = analysis?.cats_scores || {};
        const opa_violations = analysis?.opa_violations || [];
        const primary_reason = analysis?.explanation?.primary_reason || "";
        const telemetry_snapshot = analysis?.explanation?.telemetry_snapshot || {};

        const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
        const req_id = `REQ-${(telemetryRecords.length + 1).toString().padStart(4, '0')}`;

        addTelemetryRecord({
          request_id: req_id,
          timestamp,
          prompt: userPrompt,
          tag: analysis?.computed_tag || requestTag,
          strategy: meta?.strategy || "UNKNOWN",
          cloud_score: final_scores?.cloud || 0.0,
          edge_score: final_scores?.edge || 0.0,
          tier1_state: analysis?.tier1_state || "UNKNOWN",
          opa_status: analysis?.opa_status || "UNKNOWN",
          opa_violations,
          selected_route: (route_info?.site || "unknown").toUpperCase(),
          selected_model: route_info?.model || "unknown",
          latency_ms: route_info?.total_inference_ms || duration_ms,
          is_fallback: analysis?.forced_fallback || false,
          cloud_expected_cost: analysis?.explanation?.score_breakdown?.cloud_expected_cost || 0.0,
          edge_expected_cost: analysis?.explanation?.score_breakdown?.edge_expected_cost || 0.0,
          cloud_base_score: cats_scores?.cloud || 0.0,
          edge_base_score: cats_scores?.edge || 0.0,
          primary_reason: primary_reason,
          telemetry_snapshot: telemetry_snapshot
        });

      } else {
        const text = await res.text();
        const error_text = `**${t('api_err')} ${res.status}:**\n\`\`\`json\n${text}\n\`\`\``;
        addMessage({ role: "assistant", content: error_text });
      }
    } catch (error: unknown) {
      console.error(error);
      const error_text = `**${t('conn_failed')}** Gateway error: \`${(error as Error).message}\``;
      addMessage({ role: "assistant", content: error_text });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("nav_console")}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("console_desc")}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleClear} className="text-xs font-mono">
          <Trash2 className="size-3 mr-2" />
          {t("clear_history")}
        </Button>
      </div>

      <div className="flex-1 rounded-lg border border-border bg-card flex flex-col overflow-hidden">
        <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center text-muted-foreground text-sm border-dashed border-2 border-border/50 rounded-md m-4">
              Send a message to see the routing decision and response.
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`p-4 rounded-md text-sm ${
                  msg.role === "user" 
                    ? "bg-primary/10 ml-12" 
                    : "bg-secondary mr-12 whitespace-pre-wrap font-sans"
                }`}
              >
                {msg.content}
              </div>
            ))
          )}
          {loading && (
            <div className="bg-secondary mr-12 p-4 rounded-md text-sm font-mono flex items-center gap-2">
              <Loader2 className="size-4 animate-spin text-muted-foreground" />
              <span className="text-muted-foreground">{t("processing")}</span>
            </div>
          )}
        </div>
        <div className="p-4 border-t border-border bg-background">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={t("enter_prompt")}
              className="flex-1"
              disabled={loading}
            />
            <Button type="submit" disabled={loading || !prompt.trim()}>
              {loading ? <Loader2 className="animate-spin size-4" /> : <Send className="size-4" />}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
