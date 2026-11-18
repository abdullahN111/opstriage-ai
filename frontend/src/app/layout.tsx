import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpsTriage AI — Autonomous Operations Command Center",
  description:
    "End-to-end inbox operations hub powered by the Gemini API and Google Workspace APIs (Gmail, Drive, and Sheets).",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased selection:bg-indigo-500/30 selection:text-indigo-200">
        {children}
      </body>
    </html>
  );
}
