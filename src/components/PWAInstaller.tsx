"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { Download, Smartphone, X, Check, Share, PlusSquare } from "lucide-react";

export const PWAInstaller: React.FC = () => {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isStandalone, setIsStandalone] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const checkStandalone = window.matchMedia("(display-mode: standalone)").matches || (window.navigator as any).standalone;
    setIsStandalone(!!checkStandalone);

    const userAgent = window.navigator.userAgent.toLowerCase();
    const isAppleDevice = /iphone|ipad|ipod/.test(userAgent);
    setIsIOS(isAppleDevice);

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/sw.js")
        .then((reg) => {
          console.log("PWA Service Worker registered:", reg.scope);
        })
        .catch((err) => {
          console.warn("PWA Service Worker registration failed:", err);
        });
    }

    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);

    const handleOpenInstall = () => handleInstallClick();
    window.addEventListener("open-pwa-install", handleOpenInstall);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("open-pwa-install", handleOpenInstall);
    };
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const choiceResult = await deferredPrompt.userChoice;
      if (choiceResult.outcome === "accepted") {
        setDeferredPrompt(null);
      }
    } else {
      setShowModal(true);
    }
  };

  if (isStandalone) return null;

  const modalContent = showModal ? (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="relative w-full max-w-sm rounded-[28px] border border-slate-200 bg-white p-6 shadow-2xl text-slate-800">
        <button
          onClick={() => setShowModal(false)}
          className="absolute top-4 right-4 h-8 w-8 rounded-full flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3.5 mb-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-100 text-sky-700 shrink-0">
            <Smartphone className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">Cài đặt Garmin AI Coach</h3>
            <p className="text-xs text-sky-700 font-medium">Trải nghiệm ứng dụng gốc mượt mà</p>
          </div>
        </div>

        {isIOS ? (
          <div className="space-y-3 text-xs text-slate-600">
            <p className="font-medium text-slate-900">Để cài đặt trên iPhone / iPad (Safari):</p>
            <div className="flex items-start gap-3 p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
              <div className="p-1.5 rounded-lg bg-sky-100 text-sky-700 shrink-0">
                <Share className="h-4 w-4" />
              </div>
              <div>
                <strong className="text-slate-900">Bước 1:</strong> Bấm nút <strong>Chia sẻ</strong> (biểu tượng hộp có mũi tên lên ở thanh công cụ dưới Safari).
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
              <div className="p-1.5 rounded-lg bg-sky-100 text-sky-700 shrink-0">
                <PlusSquare className="h-4 w-4" />
              </div>
              <div>
                <strong className="text-slate-900">Bước 2:</strong> Cuộn xuống và chọn <strong>&ldquo;Thêm vào Màn hình chính&rdquo; (Add to Home Screen)</strong>.
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
              <div className="p-1.5 rounded-lg bg-emerald-100 text-emerald-700 shrink-0">
                <Check className="h-4 w-4" />
              </div>
              <div>
                <strong className="text-slate-900">Bước 3:</strong> Nhấn <strong>Thêm (Add)</strong>. Ứng dụng đã sẵn sàng ngay trên màn hình chính!
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-3.5 text-xs text-slate-600">
            <p className="font-medium text-slate-900">Để cài đặt trên Android / Chrome:</p>
            <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
              <p>1. Bấm vào menu <strong>Ba chấm ⋮</strong> ở góc trên bên phải trình duyệt.</p>
              <p>2. Chọn <strong>&ldquo;Cài đặt ứng dụng&rdquo; (Install App)</strong> hoặc <strong>&ldquo;Thêm vào Màn hình chính&rdquo;</strong>.</p>
            </div>
            <button
              onClick={handleInstallClick}
              className="w-full py-2.5 rounded-full bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs transition shadow-xs flex items-center justify-center gap-2"
            >
              <Download className="h-4 w-4" />
              <span>Xác nhận Cài đặt</span>
            </button>
          </div>
        )}

        <button
          onClick={() => setShowModal(false)}
          className="w-full mt-4 py-2.5 rounded-full text-xs font-medium text-sky-700 hover:bg-sky-50 transition"
        >
          Đã hiểu
        </button>
      </div>
    </div>
  ) : null;

  return mounted ? createPortal(modalContent, document.body) : null;
};
