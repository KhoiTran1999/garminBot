"use client";

import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { useAuth } from "@/lib/auth-context";
import { api, AnalysisResult, ChatMessage } from "@/lib/api";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { AudioPlayer } from "@/components/AudioPlayer";
import {
  Send,
  Sparkles,
  User,
  Bot,
  AlertCircle,
  Activity,
  Moon,
  Flame,
  BatteryCharging,
  Bandage,
  History,
  Plus,
  X,
  Target,
  Copy,
  Check,
  ChevronRight,
  MessageSquare
} from "lucide-react";

interface ExtendedChatMessage {
  role: "user" | "assistant";
  content: string;
  audio_url?: string | null;
  mode?: string;
  metrics?: {
    readiness_score?: number | null;
    is_fresh?: boolean;
    fresh_msg?: string;
    date?: string;
  };
}

export default function ChatFirstPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ExtendedChatMessage[]>([]);
  const [historyList, setHistoryList] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [mounted, setMounted] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const quickActionPrompts = [
    {
      id: "daily",
      label: "Hôm nay nên chạy bài gì?",
      desc: "Tính Readiness & giáo án chạy",
      icon: Activity,
      color: "text-sky-600",
      bgColor: "bg-sky-50",
      isAnalysis: true,
    },
    {
      id: "sleep_analysis",
      label: "Đánh giá giấc ngủ đêm qua",
      desc: "Chi tiết 3 pha ngủ & HRV",
      icon: Moon,
      color: "text-indigo-600",
      bgColor: "bg-indigo-50",
      isAnalysis: true,
    },
    {
      id: "battery",
      label: "Bắt mạch Body Battery",
      desc: "Đánh giá pin năng lượng & stress",
      icon: BatteryCharging,
      color: "text-emerald-600",
      bgColor: "bg-emerald-50",
      isAnalysis: true,
    },
    {
      id: "workout",
      label: "Phân tích buổi tập vừa rồi",
      desc: "Splits, HR zone & cardiac drift",
      icon: Flame,
      color: "text-amber-600",
      bgColor: "bg-amber-50",
      isAnalysis: true,
    },
    {
      id: "rhr_recovery",
      label: "Đánh giá RHR & HRV phục hồi",
      desc: "Nhịp tim nghỉ ngơi & hồi phục",
      icon: Sparkles,
      color: "text-sky-600",
      bgColor: "bg-sky-50",
      isAnalysis: false,
      text: "Đánh giá nhịp tim nghỉ ngơi (RHR) và độ phục hồi HRV của tôi đêm qua?",
    },
    {
      id: "injury_advice",
      label: "Tư vấn căng cơ & chấn thương",
      desc: "Chăm sóc cơ bắp sau chạy",
      icon: Bandage,
      color: "text-rose-600",
      bgColor: "bg-rose-50",
      isAnalysis: false,
      text: "Tôi bị mỏi bắp chuối sau buổi chạy hôm qua, hôm nay có nên chạy tiếp không?",
    },
  ];

  useEffect(() => {
    setMounted(true);
    fetchHistoryOnly();

    const handleToggleDrawer = () => setDrawerOpen((prev) => !prev);
    window.addEventListener("toggle-chat-history", handleToggleDrawer);

    return () => {
      window.removeEventListener("toggle-chat-history", handleToggleDrawer);
    };
  }, []);

  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  const fetchHistoryOnly = async () => {
    setLoadingHistory(true);
    try {
      const res = await api.getChatHistory();
      if (res.history) {
        setHistoryList(res.history);
      }
    } catch (e) {
      console.warn("Lỗi tải lịch sử:", e);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setInput("");
    setError(null);
    setDrawerOpen(false);
  };

  const handleRestoreHistory = () => {
    if (historyList.length > 0) {
      setMessages(historyList);
    }
    setDrawerOpen(false);
  };

  const handleSelectHistoryItem = (item: ChatMessage) => {
    setMessages([
      { role: "user", content: item.content },
    ]);
    setDrawerOpen(false);
    handleSend(item.content);
  };

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || loading) return;

    setError(null);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    const newMsg: ExtendedChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, newMsg]);

    setLoading(true);
    try {
      const res = await api.sendChatMessage(text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.reply,
        },
      ]);
      fetchHistoryOnly();
    } catch (err: any) {
      setError(err.message || "Lỗi gửi câu hỏi. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerAnalysis = async (mode: string, label: string) => {
    if (loading) return;
    setError(null);

    const userPrompt = `${label}`;
    setMessages((prev) => [...prev, { role: "user", content: userPrompt }]);

    setLoading(true);
    try {
      const result: AnalysisResult = await api.runAnalysis(mode);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.report,
          audio_url: result.audio_url,
          mode: result.mode,
          metrics: result.metrics,
        },
      ]);
      fetchHistoryOnly();
    } catch (err: any) {
      setError(err.message || "Lỗi phân tích Garmin. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (content: string, idx: number) => {
    navigator.clipboard.writeText(content);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  const historyDrawer = (
    <div className="fixed inset-0 z-50 flex">
      <div
        onClick={() => setDrawerOpen(false)}
        className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity"
      />
      <div 
        className="relative w-80 max-w-[85vw] bg-white border-r border-slate-200 rounded-r-[28px] p-5 flex flex-col shadow-2xl z-10 pt-safe pb-safe"
        style={{ 
          paddingTop: "max(1.5rem, env(safe-area-inset-top, 0px))", 
          paddingBottom: "max(1.5rem, env(safe-area-inset-bottom, 0px))" 
        }}
      >
        {/* Header Drawer */}
        <div className="flex items-center justify-between pb-3.5 border-b border-slate-100 mb-3 px-1">
          <div className="flex items-center gap-2">
            <History className="h-5 w-5 text-sky-600" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Lịch sử Hội thoại</h3>
          </div>
          <button
            onClick={() => setDrawerOpen(false)}
            className="h-8 w-8 rounded-full flex items-center justify-center text-slate-500 hover:bg-slate-100 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Nút bắt đầu Chat Mới */}
        <button
          onClick={handleNewChat}
          className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-full bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs mb-3 transition shadow-xs"
        >
          <Plus className="h-4 w-4" />
          <span>Bắt đầu cuộc trò chuyện mới</span>
        </button>

        {/* Danh sách các câu hỏi cũ */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 text-xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 px-1">
            Các câu hỏi gần đây ({historyList.filter(h => h.role === "user").length})
          </div>

          {historyList.length === 0 ? (
            <div className="p-4 text-center text-slate-400 text-xs">
              Chưa có lịch sử hội thoại nào được lưu.
            </div>
          ) : (
            historyList
              .filter((item) => item.role === "user")
              .map((item, idx) => (
                <div
                  key={idx}
                  onClick={() => handleSelectHistoryItem(item)}
                  className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 hover:bg-slate-100 text-slate-800 cursor-pointer transition flex items-center justify-between gap-2 shadow-2xs"
                >
                  <div className="flex items-center gap-2.5 truncate flex-1">
                    <MessageSquare className="h-4 w-4 text-sky-600 shrink-0" />
                    <span className="truncate font-medium">{item.content}</span>
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />
                </div>
              ))
          )}

          {historyList.length > 0 && (
            <div className="pt-3 border-t border-slate-100">
              <button
                onClick={handleRestoreHistory}
                className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-full border border-slate-300 text-xs font-medium text-sky-700 hover:bg-sky-50 transition"
              >
                <span>Mở lại toàn bộ phiên trước</span>
              </button>
            </div>
          )}
        </div>

        {/* Thông tin nhanh hồ sơ */}
        <div className="pt-3 border-t border-slate-100 text-xs text-slate-600 space-y-1 px-1">
          <div className="flex items-center gap-2">
            <Target className="h-4 w-4 text-sky-600 shrink-0" />
            <span className="truncate font-medium">{user?.goal || "Chạy bộ"}</span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col flex-1 min-h-0 h-full max-w-3xl mx-auto w-full overflow-hidden bg-[#f8f9fc]">
      {/* KHUNG CHAT: Nếu chưa có tin nhắn, hiển thị màn hình New Chat sáng sủa */}
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-6 sm:py-8 text-center overflow-y-auto w-full">
          {/* Logo & Lời chào Material Design 3 */}
          <div className="w-14 h-14 rounded-2xl bg-sky-600 text-white flex items-center justify-center shadow-md shadow-sky-600/20 mb-4">
            <Activity className="h-7 w-7" />
          </div>

          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mb-1.5 tracking-tight">
            Xin chào, {user?.name || "Vận động viên"}! 👋
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 max-w-xs sm:max-w-md mb-6 leading-relaxed">
            Tôi là HLV AI Garmin cá nhân của bạn. Hôm nay bạn muốn lên giáo án chạy, kiểm tra giấc ngủ hay phục hồi thể trạng?
          </p>

          {/* 4 Gợi ý kịch bản 1-chạm (Clean Material 3 Cards) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg text-left mb-5">
            {quickActionPrompts.slice(0, 4).map((p) => {
              const Icon = p.icon;
              return (
                <button
                  key={p.id}
                  onClick={() => handleTriggerAnalysis(p.id, p.label)}
                  disabled={loading}
                  className="p-3.5 rounded-2xl bg-white border border-slate-200/90 hover:border-sky-300 hover:shadow-md transition-all flex items-center justify-between gap-3 group text-left active:scale-[0.98] shadow-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className={`h-10 w-10 rounded-xl ${p.bgColor} flex items-center justify-center shrink-0`}>
                      <Icon className={`h-5 w-5 ${p.color}`} />
                    </div>
                    <div>
                      <h4 className="text-xs sm:text-sm font-semibold text-slate-800 group-hover:text-sky-600 transition-colors">
                        {p.label}
                      </h4>
                      <p className="text-[11px] text-slate-500 mt-0.5">{p.desc}</p>
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-sky-600 transition shrink-0" />
                </button>
              );
            })}
          </div>

          {/* Nút xem lịch sử */}
          {historyList.length > 0 && (
            <button
              onClick={() => setDrawerOpen(true)}
              className="text-xs text-slate-600 hover:text-sky-700 flex items-center gap-2 transition py-2 px-4 rounded-full hover:bg-white hover:shadow-xs border border-transparent hover:border-slate-200"
            >
              <History className="h-4 w-4 text-sky-600" />
              <span>Xem lại {historyList.length} câu hỏi trong lịch sử</span>
            </button>
          )}
        </div>
      ) : (
        /* DÒNG HỘI THOẠI KHI ĐANG CHAT */
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-4">
          {messages.map((m, idx) => {
            const isUser = m.role === "user";
            return (
              <div
                key={idx}
                className={`flex items-start gap-2.5 ${isUser ? "flex-row-reverse" : "flex-row"}`}
              >
                {/* Avatar */}
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                    isUser
                      ? "bg-sky-600 text-white shadow-xs"
                      : "bg-white text-sky-600 border border-slate-200 shadow-xs"
                  }`}
                >
                  {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>

                {/* Bong bóng tin nhắn */}
                <div
                  className={`max-w-[88%] sm:max-w-[82%] rounded-[20px] p-4 text-xs sm:text-sm leading-relaxed shadow-xs ${
                    isUser
                      ? "bg-sky-600 text-white rounded-tr-[4px] font-normal"
                      : "bg-white text-slate-900 border border-slate-200/90 rounded-tl-[4px] space-y-3"
                  }`}
                >
                  {/* Header tin nhắn AI */}
                  {!isUser && (
                    <div className="flex items-center justify-between pb-2 border-b border-slate-100 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 tracking-tight">Garmin Coach</span>
                        <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-semibold text-sky-800">AI</span>
                      </div>

                      <button
                        onClick={() => handleCopy(m.content, idx)}
                        title="Sao chép"
                        className="text-slate-500 hover:text-sky-600 text-[11px] flex items-center gap-1.5 px-2 py-1 rounded-full hover:bg-slate-100 transition"
                      >
                        {copiedIdx === idx ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-600" />
                            <span className="text-emerald-600 font-medium">Đã chép</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            <span>Sao chép</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}

                  {/* Thẻ tóm tắt chỉ số thể trạng */}
                  {m.metrics && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs">
                      {m.metrics.readiness_score !== undefined && m.metrics.readiness_score !== null && (
                        <div>
                          <span className="text-[10px] text-slate-500 block font-medium">Điểm sẵn sàng</span>
                          <span className="font-bold text-amber-600 text-sm">
                            {m.metrics.readiness_score}/100
                          </span>
                        </div>
                      )}
                      <div>
                        <span className="text-[10px] text-slate-500 block font-medium">Garmin Connect</span>
                        <span className={`font-semibold text-xs ${m.metrics.is_fresh ? "text-emerald-600" : "text-amber-600"}`}>
                          {m.metrics.is_fresh ? "Đã đồng bộ" : "Chờ đồng bộ"}
                        </span>
                      </div>
                      {m.metrics.date && (
                        <div>
                          <span className="text-[10px] text-slate-500 block font-medium">Ngày phân tích</span>
                          <span className="font-medium text-slate-800 text-xs">{m.metrics.date}</span>
                        </div>
                      )}
                      {m.mode && (
                        <div>
                          <span className="text-[10px] text-slate-500 block font-medium">Chế độ</span>
                          <span className="font-bold text-sky-600 uppercase text-xs">{m.mode}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Nội dung phản hồi */}
                  {isUser ? (
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  ) : (
                    <MarkdownRenderer content={m.content} />
                  )}

                  {/* Trình phát âm thanh nếu có */}
                  {m.audio_url && (
                    <div className="pt-2 border-t border-slate-100">
                      <AudioPlayer src={m.audio_url} title={`Voice Coach - ${m.mode ? m.mode.toUpperCase() : "HLV AI"}`} />
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Đang tải phản hồi */}
          {loading && (
            <div className="flex items-start gap-2.5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-sky-600 border border-slate-200 shadow-xs">
                <Bot className="h-4 w-4" />
              </div>
              <div className="rounded-[20px] rounded-tl-[4px] border border-slate-200 bg-white p-4 text-xs text-slate-600 flex items-center gap-2.5 shadow-xs">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-sky-600 border-t-transparent" />
                <span>HLV AI đang tra cứu dữ liệu Garmin và chuẩn bị câu trả lời...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Thông báo lỗi */}
      {error && (
        <div className="mx-4 sm:mx-6 mb-2 p-3.5 rounded-2xl border border-red-200 bg-red-50 text-xs text-red-700 flex items-center justify-between gap-2 shrink-0 shadow-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-600 shrink-0" />
            <span className="font-medium">{error}</span>
          </div>
          <button 
            onClick={() => setError(null)} 
            className="text-red-700 hover:opacity-80 p-1 rounded-full"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Ô NHẬP LIỆU DÍNH ĐÁY (Material 3 Light Dock Bar) */}
      <div 
        className="px-4 sm:px-6 pt-2 pb-safe border-t border-slate-200 bg-white/95 backdrop-blur-md shrink-0 z-20"
        style={{ paddingBottom: "max(1.25rem, env(safe-area-inset-bottom, 0px))" }}
      >
        <div className="flex items-end gap-2 bg-slate-50 hover:bg-slate-100/70 focus-within:bg-white border border-slate-300 focus-within:border-sky-500 focus-within:ring-2 focus-within:ring-sky-100 rounded-3xl px-4 py-2 transition shadow-xs">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Hỏi HLV AI điều gì đó..."
            rows={1}
            className="w-full resize-none bg-transparent py-1 px-1 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none max-h-28"
          />

          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-sky-600 text-white hover:bg-sky-500 disabled:opacity-30 disabled:pointer-events-none transition-all shrink-0 mb-0.5 active:scale-95 shadow-xs"
            title="Gửi câu hỏi"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Render History Drawer via Portal */}
      {mounted && drawerOpen && createPortal(historyDrawer, document.body)}
    </div>
  );
}
