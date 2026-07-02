import type { Metadata } from "next";
import { Inter, Fira_Code } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ThemeProvider } from "@/components/theme-provider";
import { I18nProvider } from "@/lib/i18n";
import { Toaster } from "sonner";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const firaCode = Fira_Code({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CATS Control Plane",
  description: "Enterprise AI Orchestration Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable} ${firaCode.variable}`}>
      <body className="h-screen bg-background text-foreground flex overflow-hidden antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <I18nProvider>
            <Sidebar />
            <div className="flex-1 flex flex-col h-full min-w-0">
              <Header />
              <main className="flex-1 overflow-y-auto p-6">
                <div className="max-w-6xl mx-auto">
                  {children}
                </div>
              </main>
            </div>
            <Toaster theme="system" richColors />
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
