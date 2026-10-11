import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

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
          <main className="flex-1 w-full flex flex-col min-h-0">
            {children}
          </main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
