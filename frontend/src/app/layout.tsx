import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DASMO Office | AI YouTube Shorts Factory",
  description: "Administrative console and real-time orchestrator for automated YouTube Shorts creation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="antialiased font-sans bg-dasmo-dark text-slate-100">
        {children}
      </body>
    </html>
  );
}
