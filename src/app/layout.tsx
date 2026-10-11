import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Garmin AI Coach Pro",
  description: "Huấn luyện viên chạy bộ cá nhân hóa với Garmin Connect & Google Gemini AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen antialiased flex flex-col">
        <AuthProvider>
          <Navbar />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {children}
          </main>
          <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-400">
            <p>Garmin AI Coach Pro • Vercel & Notion Integrated</p>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
