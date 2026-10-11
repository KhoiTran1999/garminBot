"use client";

import React, { useState, useEffect } from "react";
import { Download, Smartphone, X, Check, Share, PlusSquare } from "lucide-react";

export const PWAInstaller: React.FC = () => {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isStandalone, setIsStandalone] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    // 1. Kiểm tra standalone mode (đã cài đặt chưa)
    const checkStandalone = window.matchMedia("(display-mode: standalone)").matches || (window.navigator as any).standalone;
    setIsStandalone(!!checkStandalone);

    // 2. Nhận biết thiết bị iOS
    const userAgent = window.navigator.userAgent.toLowerCase();
    const isAppleDevice = /iphone|ipad|ipod/.test(userAgent);
    setIsIOS(isAppleDevice);

    // 3. Đăng ký Service Worker
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

    // 4. Bắt sự kiện beforeinstallprompt trên Android & Chrome
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);

    // Lắng nghe sự kiện mở modal từ Navbar
    const handleOpenInstall = () => handleInstallClick();
    window.addEventListener("open-pwa-install", handleOpenInstall);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("open-pwa-install", handleOpenInstall);
    };
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      // Android / Chrome / Edge native install prompt
      deferredPrompt.prompt();
      const choiceResult = await deferredPrompt.userChoice;
      if (choiceResult.outcome === "accepted") {
        setDeferredPrompt(null);
      }
    } else {
      // iOS hoặc các trình duyệt cần hướng dẫn tay
      setShowModal(true);
    }
  };

  // Không hiển thị nếu đã chạy trong môi trường App standalone
  if (isStandalone) return null;

  return (
    <>
      {/* Modal hướng dẫn cài đặt nếu không hỗ trợ trigger tự động */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="relative w-full max-w-sm rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-2xl text-slate-200">
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-4 right-4 p-1 text-slate-400 hover:text-white rounded-lg"
            >
              <X className="h-4 w-4" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                <Smartphone className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Cài đặt Garmin AI Coach</h3>
                <p className="text-[11px] text-cyan-400">Trải nghiệm như ứng dụng gốc</p>
              </div>
            </div>

            {isIOS ? (
              <div className="space-y-3 text-xs text-slate-300">
                <p>Để cài đặt ứng dụng trên iPhone / iPad (Safari):</p>
                <div className="flex items-start gap-2.5 p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="p-1 rounded bg-slate-800 text-cyan-400 shrink-0">
                    <Share className="h-4 w-4" />
                  </div>
                  <div>
                    <strong>Bước 1:</strong> Bấm nút <strong>Chia sẻ</strong> (biểu tượng hộp có mũi tên lên ở thanh công cụ dưới Safari).
                  </div>
                </div>
                <div className="flex items-start gap-2.5 p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="p-1 rounded bg-slate-800 text-cyan-400 shrink-0">
                    <PlusSquare className="h-4 w-4" />
                  </div>
                  <div>
                    <strong>Bước 2:</strong> Cuộn xuống và chọn <strong>&ldquo;Thêm vào Màn hình chính&rdquo; (Add to Home Screen)</strong>.
                  </div>
                </div>
                <div className="flex items-start gap-2.5 p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="p-1 rounded bg-emerald-500/20 text-emerald-400 shrink-0">
                    <Check className="h-4 w-4" />
                  </div>
                  <div>
                    <strong>Bước 3:</strong> Nhấn <strong>Thêm (Add)</strong>. Ứng dụng sẽ xuất hiện trên màn hình điện thoại của bạn!
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-3 text-xs text-slate-300">
                <p>Để cài đặt ứng dụng trên Android / Chrome:</p>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                  <p>1. Bấm vào menu <strong>Ba chấm ⋮</strong> ở góc trên bên phải trình duyệt.</p>
                  <p>2. Chọn <strong>&ldquo;Cài đặt ứng dụng&rdquo; (Install App)</strong> hoặc <strong>&ldquo;Thêm vào Màn hình chính&rdquo;</strong>.</p>
                </div>
                <button
                  onClick={handleInstallClick}
                  className="w-full py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition shadow-md shadow-cyan-500/20 flex items-center justify-center gap-2"
                >
                  <Download className="h-4 w-4" />
                  <span>Xác nhận Cài đặt</span>
                </button>
              </div>
            )}

            <button
              onClick={() => setShowModal(false)}
              className="w-full mt-4 py-2 rounded-xl border border-slate-800 text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              Đã hiểu
            </button>
          </div>
        </div>
      )}
    </>
  );
};
