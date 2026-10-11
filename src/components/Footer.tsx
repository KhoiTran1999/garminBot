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
    <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-400 shrink-0">
      <p>Garmin AI Coach Pro • Vercel & Notion Integrated</p>
    </footer>
  );
};
