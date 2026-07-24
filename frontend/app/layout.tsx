import type { Metadata, Viewport } from "next";
import { AppHeader } from "@/components/app-header";
import { AssistantProvider } from "@/contexts/assistant-provider";
import { AssistantPanel } from "@/components/assistant/assistant-panel";
import "./globals.css";

export const metadata: Metadata = {
  title: "ADME Lens | Computational ADME Explorer",
  description: "Local computational ADME and ADMET exploration for small-molecule SMILES.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  themeColor: "#f4f7f5",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <a className="skip-link" href="#main-content">Skip to main content</a>
        <AssistantProvider>
          <AppHeader />
          {children}
          <AssistantPanel />
        </AssistantProvider>
      </body>
    </html>
  );
}
