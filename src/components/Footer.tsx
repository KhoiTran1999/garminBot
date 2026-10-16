"use client";

import React from "react";
import { usePathname } from "next/navigation";

export const Footer: React.FC = () => {
  const pathname = usePathname();

  // Ẩn hoàn toàn Footer ở trang Chat chính và trang login để ô chat dính đáy chuẩn UX
  if (pathname === "/" || pathname === "/chat" || pathname === "/login") {
    return null;
  }

  return (
    <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-500 shrink-0 bg-white">
      <p>Garmin AI Coach Pro • Vercel & Notion Integrated • Material Design 3</p>
    </footer>
  );
};
