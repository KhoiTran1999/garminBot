"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { 
  Activity, 
  Moon, 
  Flame, 
  BatteryCharging, 
  MessageSquare, 
  User, 
  LogOut, 
  Menu, 
  X,
  History,
  RefreshCw,
  Download
} from "lucide-react";

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (pathname === "/login") return null;

  const isChatPage = pathname === "/" || pathname === "/chat";

  const navItems = [
    { name: "HLV AI Chat", href: "/", icon: MessageSquare },
    { name: "Sức khỏe ngày", href: "/daily", icon: Activity },
    { name: "Giấc ngủ", href: "/sleep", icon: Moon },
    { name: "Buổi tập", href: "/workout", icon: Flame },
    { name: "Pin & Năng lượng", href: "/battery", icon: BatteryCharging },
    { name: "Hồ sơ", href: "/profile", icon: User },
  ];

  const handleSyncClick = () => {
    setSyncing(true);
    window.dispatchEvent(new CustomEvent("refresh-garmin-sync"));
    setTimeout(() => setSyncing(false), 2000);
  };

  const mobileDrawer = (
    <div className="fixed inset-0 z-50 flex">
      <div 
        onClick={() => setMobileMenuOpen(false)} 
        className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity" 
      />
      <div 
        className="relative w-72 max-w-[85vw] bg-white border-r border-slate-200 rounded-r-[28px] p-5 flex flex-col shadow-2xl z-10 pt-safe pb-safe"
        style={{ 
          paddingTop: "max(1.5rem, env(safe-area-inset-top, 0px))", 
          paddingBottom: "max(1.5rem, env(safe-area-inset-bottom, 0px))" 
        }}
      >
        {/* Header Drawer */}
        <div className="flex items-center justify-between pb-4 mb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-100 text-sky-700">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <span className="text-sm font-bold text-slate-900 block leading-none">Garmin AI Coach</span>
              <span className="text-[10px] text-slate-500 font-medium">Material Design 3</span>
            </div>
          </div>
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="h-8 w-8 rounded-full flex items-center justify-center text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Destinations */}
        <div className="flex-1 space-y-1.5 overflow-y-auto py-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3.5 px-4 py-3 rounded-full text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-sky-100 text-sky-900 font-semibold shadow-xs"
                    : "text-slate-700 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? "text-sky-600" : "text-slate-500"}`} />
                {item.name}
              </Link>
            );
          })}

          <div className="pt-3">
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                window.dispatchEvent(new CustomEvent("open-pwa-install"));
              }}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-full text-sm font-medium text-sky-800 bg-sky-50 hover:bg-sky-100 border border-sky-200 transition"
            >
              <Download className="h-5 w-5 text-sky-600" />
              <span>Cài đặt Ứng dụng (App)</span>
            </button>
          </div>
        </div>

        {user && (
          <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
            <div className="truncate pr-2">
              <p className="text-xs font-semibold text-slate-900 truncate">{user.name}</p>
              <p className="text-[10px] text-slate-500 truncate">{user.email}</p>
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 transition shrink-0"
            >
              <LogOut className="h-3.5 w-3.5" />
              Đăng xuất
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <nav 
      className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-xs pt-safe"
      style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-3">
          {/* Logo & History Toggle on Chat */}
          <div className="flex items-center gap-2 sm:gap-3">
            {isChatPage && (
              <button
                onClick={() => window.dispatchEvent(new CustomEvent("toggle-chat-history"))}
                title="Lịch sử hội thoại"
                className="h-10 w-10 rounded-full flex items-center justify-center text-sky-700 hover:bg-sky-50 active:bg-sky-100 transition-colors"
                aria-label="Lịch sử trò chuyện"
              >
                <History className="h-5 w-5" />
              </button>
            )}

            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-600 text-white shadow-xs group-hover:scale-105 transition-transform">
                <Activity className="h-5 w-5" />
              </div>
              <div className="flex flex-col">
                <span className="text-sm sm:text-base font-bold tracking-tight text-slate-900 flex items-center gap-1.5 leading-none">
                  GARMIN <span className="text-sky-600 font-extrabold">AI COACH</span>
                  <span className="hidden sm:inline rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-semibold text-sky-800">PRO</span>
                </span>
                <span className="hidden sm:block text-[9px] text-slate-500 tracking-wider mt-0.5">NOTION & VERCEL POWERED</span>
              </div>
            </Link>
          </div>

          {/* Desktop Nav Items (Material 3 Navigation Bar pills) */}
          <div className="hidden lg:flex lg:items-center lg:space-x-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-medium transition-all ${
                    isActive
                      ? "bg-sky-100 text-sky-900 font-semibold shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-sky-600" : "text-slate-500"}`} />
                  {item.name}
                </Link>
              );
            })}
          </div>

          {/* User badge, Sync & Mobile menu */}
          <div className="flex items-center gap-2">
            {/* Quick Garmin sync status button */}
            {isChatPage && (
              <button
                onClick={handleSyncClick}
                title="Kiểm tra đồng bộ Garmin"
                className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs text-slate-700 transition"
              >
                <RefreshCw className={`h-3.5 w-3.5 text-sky-600 ${syncing ? "animate-spin" : ""}`} />
                <span className="hidden md:inline font-medium">Đồng bộ</span>
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
              </button>
            )}

            {/* Install PWA Button */}
            <button
              onClick={() => window.dispatchEvent(new CustomEvent("open-pwa-install"))}
              title="Cài đặt App vào điện thoại / máy tính"
              className="hidden sm:flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-50 text-sky-800 border border-sky-200 hover:bg-sky-100 text-xs font-medium transition shadow-xs"
            >
              <Download className="h-4 w-4 text-sky-600" />
              <span>Cài đặt App</span>
            </button>

            {user && (
              <div className="hidden md:flex items-center gap-2.5 pl-2 border-l border-slate-200">
                <Link href="/profile" className="text-right hover:opacity-85 transition">
                  <p className="text-xs font-semibold text-slate-900 leading-tight">{user.name}</p>
                  <p className="text-[10px] text-sky-600 max-w-[120px] truncate leading-tight font-medium">{user.goal || "Chạy bộ"}</p>
                </Link>
                <button
                  onClick={logout}
                  title="Đăng xuất"
                  className="h-9 w-9 rounded-full flex items-center justify-center text-slate-500 hover:bg-red-50 hover:text-red-600 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            )}

            {/* Mobile hamburger icon button */}
            <div className="flex lg:hidden">
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="h-10 w-10 rounded-full flex items-center justify-center text-slate-700 hover:bg-slate-100 transition"
                title="Menu"
                aria-label="Menu điều hướng"
              >
                {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Render drawer via Portal to prevent any backdrop-filter containing block trap */}
      {mounted && mobileMenuOpen && createPortal(mobileDrawer, document.body)}
    </nav>
  );
};
