import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Suspense } from "react";
import { BottomTabs } from "@/components/nav";
import { THEME_SCRIPT } from "@/lib/theme";
import { TopBar, TopBarShell } from "@/components/top-bar";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: "EmberScan", template: "%s · EmberScan" },
  description:
    "Turn a phone walkaround video into a measured, rule-by-rule wildfire defensible-space assessment.",
};

export const viewport: Viewport = {
  themeColor: "#2b2421",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="light"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col bg-bg text-ink">
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <Suspense fallback={<TopBarShell />}>
          <TopBar />
        </Suspense>
        <div id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 pt-5 pb-28 lg:pb-12">
          {children}
        </div>
        <Suspense fallback={null}>
          <BottomTabs />
        </Suspense>
      </body>
    </html>
  );
}
