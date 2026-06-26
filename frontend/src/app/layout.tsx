import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

import { AppShell } from "@/components/shell/AppShell";
import { ReviewProvider } from "@/context/ReviewProvider";
import { ThemeProvider } from "@/context/ThemeProvider";

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
  variable: "--font-plex-sans",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "Compliance Validation Agent",
  description: "Validate repositories for SOC 2 & GDPR compliance.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${ibmPlexSans.variable} ${ibmPlexMono.variable}`}>
        <ThemeProvider>
          <ReviewProvider>
            <AppShell>{children}</AppShell>
          </ReviewProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
