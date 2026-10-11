"use client";

import React, { useState } from "react";
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
  RefreshCw
} from "lucide-react";

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);

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

  return (
    <nav className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-3 sm:px-6 lg:px-8">
        <div className="flex h-13 sm:h-14 items-center justify-between gap-2">
          {/* Logo & History toggle on Chat */}
          <div className="flex items-center gap-2 sm:gap-3">
            {isChatPage && (
              <button
                onClick={() => window.dispatchEvent(new CustomEvent("toggle-chat-history"))}
                title="Lịch sử hội thoại"
                className="p-1.5 rounded-lg border border-slate-800 bg-slate-900/90 text-cyan-400 hover:text-white hover:bg-slate-800 transition"
              >
                <History className="h-4 w-4" />
              </button>
            )}

            <Link href="/" className="flex items-center gap-2 group">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/20 group-hover:scale-105 transition-transform">
                <Activity className="h-4 w-4 text-white" />
              </div>
              <div className="flex flex-col">
                <span className="text-sm sm:text-base font-bold tracking-tight text-white flex items-center gap-1.5 leading-none">
                  GARMIN <span className="text-cyan-400 font-extrabold">AI COACH</span>
                  <span className="hidden sm:inline rounded bg-cyan-950 px-1 py-0.5 text-[9px] font-semibold text-cyan-400 border border-cyan-800">PRO</span>
                </span>
                <span className="hidden sm:block text-[9px] text-slate-400 tracking-wider mt-0.5">NOTION & VERCEL POWERED</span>
              </div>
            </Link>
          </div>

          {/* Desktop Nav Items */}
          <div className="hidden lg:flex lg:items-center lg:space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? "bg-slate-800 text-cyan-400 border border-slate-700/80 shadow-sm"
                      : "text-slate-300 hover:bg-slate-900 hover:text-white"
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
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
                className="flex items-center gap-1.5 px-2 py-1 rounded-lg border border-slate-800/80 bg-slate-900/60 hover:bg-slate-800 text-[11px] text-slate-300 hover:text-white transition"
              >
                <RefreshCw className={`h-3 w-3 text-cyan-400 ${syncing ? "animate-spin" : ""}`} />
                <span className="hidden md:inline">Đồng bộ</span>
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              </button>
            )}

            {user && (
              <div className="hidden md:flex items-center gap-2.5 pl-2 border-l border-slate-800">
                <Link href="/profile" className="text-right hover:opacity-80 transition">
                  <p className="text-xs font-semibold text-white leading-tight">{user.name}</p>
                  <p className="text-[10px] text-cyan-400 max-w-[120px] truncate leading-tight">{user.goal || "Chạy bộ"}</p>
                </Link>
                <button
                  onClick={logout}
                  title="Đăng xuất"
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-red-950/40 hover:text-red-400 border border-slate-800 transition-colors"
                >
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              </div>
            )}

            {/* Mobile hamburger */}
            <div className="flex lg:hidden">
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-900 hover:text-white"
                title="Menu"
              >
                {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-b border-slate-800 bg-slate-950 px-3 pt-2 pb-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium ${
                  isActive
                    ? "bg-slate-800 text-cyan-400 border border-slate-700"
                    : "text-slate-300 hover:bg-slate-900 hover:text-white"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.name}
              </Link>
            );
          })}
          {user && (
            <div className="pt-2.5 mt-2 border-t border-slate-800 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-white">{user.name}</p>
                <p className="text-[10px] text-slate-400">{user.email}</p>
              </div>
              <button
                onClick={logout}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold text-red-400 bg-red-950/40 border border-red-900/50"
              >
                <LogOut className="h-3 w-3" />
                Đăng xuất
              </button>
            </div>
          )}
        </div>
      )}
    </nav>
  );
};
