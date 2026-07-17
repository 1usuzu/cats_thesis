"use client";

import { KeyRound, Moon, Sun } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useTheme } from "next-themes";
import { useI18n } from "@/lib/i18n";
import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

export function Header() {
  const { setTheme, theme } = useTheme();
  const { lang, setLang, t } = useI18n();
  const [mounted, setMounted] = useState(false);
  const router = useRouter();
  const supabase = createClient();
  
  const { apiKey, setApiKey, strategy, setStrategy, requestTag, setRequestTag, clearMessages, clearTelemetryRecords } = useAppStore();

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  const handleStrategyChange = (newStrategy: string) => {
    setStrategy(newStrategy);
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    clearMessages();
    clearTelemetryRecords();
    router.push("/login");
  };

  return (
    <header className="h-14 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative w-72">
          <KeyRound className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
          <Input 
            type="password" 
            placeholder={t("api_key_placeholder")}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full bg-secondary/50 border-none pl-9 h-9 text-sm focus-visible:ring-1 font-mono placeholder:font-sans" 
          />
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">{t("strategy")}</span>
          <Select value={strategy} onValueChange={(v) => handleStrategyChange(v as string)}>
            <SelectTrigger className="w-32 h-8 text-xs font-mono border-none bg-secondary/50 focus:ring-1">
              <SelectValue placeholder={t("strategy")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="PROPOSED" className="font-mono text-xs">PROPOSED</SelectItem>
              <SelectItem value="BASELINE-1" className="font-mono text-xs">BASELINE-1</SelectItem>
              <SelectItem value="BASELINE-2" className="font-mono text-xs">BASELINE-2</SelectItem>
              <SelectItem value="BASELINE-3" className="font-mono text-xs">BASELINE-3</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">{t("request_label")}</span>
          <Select value={requestTag} onValueChange={(v) => setRequestTag(v as string)}>
            <SelectTrigger className="w-32 h-8 text-xs font-mono border-none bg-secondary/50 focus:ring-1">
              <SelectValue placeholder={t("request_label")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default" className="font-mono text-xs">default</SelectItem>
              <SelectItem value="fast_ok" className="font-mono text-xs">fast_ok</SelectItem>
              <SelectItem value="high_quality" className="font-mono text-xs">high_quality</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="h-4 w-px bg-border" />
        
        <button 
          onClick={() => setLang(lang === "EN" ? "VI" : "EN")}
          className="text-muted-foreground hover:text-foreground transition-colors flex items-center justify-center size-8 rounded-md hover:bg-secondary text-xs font-bold"
          title="Toggle Language"
        >
          {lang}
        </button>

        {mounted && (
          <button 
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="text-muted-foreground hover:text-foreground transition-colors flex items-center justify-center size-8 rounded-md hover:bg-secondary"
            title="Toggle Theme"
          >
            {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
        )}
        
        <button 
          onClick={handleLogout}
          className="text-destructive hover:text-destructive-foreground hover:bg-destructive transition-colors flex items-center justify-center size-8 rounded-md"
          title="Logout"
        >
          <LogOut className="size-4" />
        </button>
      </div>
    </header>
  );
}
