import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "NimbleVault – AI Video Pipeline",
  description:
    "Automated AI-powered video content handler that bridges Google Drive cloud storage and YouTube distribution. Powered by Gemini AI.",
  keywords: ["video pipeline", "google drive", "youtube", "ai", "automation", "gemini"],
  authors: [{ name: "NimbleVault" }],
  openGraph: {
    title: "NimbleVault – AI Video Pipeline",
    description: "Automate your video workflow from Google Drive to YouTube with Gemini AI",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} dark`}>
      <body className="min-h-screen bg-dark-900 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
