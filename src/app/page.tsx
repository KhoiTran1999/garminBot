"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
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
  RefreshCw,
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
  // Khởi tạo màn hình Chat Mới (không lôi tin nhắn cũ ra làm rối mắt)
  const [messages, setMessages] = useState<ExtendedChatMessage[]>([]);
  const [historyList, setHistoryList] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const quickActionPrompts = [
    {
      id: "daily",
      label: "Hôm nay nên chạy bài gì?",
      desc: "Tính Readiness & giáo án chạy",
      icon: Activity,
      color: "text-cyan-400",
      isAnalysis: true,
    },
    {
      id: "sleep_analysis",
      label: "Đánh giá giấc ngủ đêm qua",
      desc: "Chi tiết 3 pha ngủ & HRV",
      icon: Moon,
      color: "text-indigo-400",
      isAnalysis: true,
    },
    {
      id: "battery",
      label: "Bắt mạch Body Battery",
      desc: "Đánh giá pin năng lượng & stress",
      icon: BatteryCharging,
      color: "text-emerald-400",
      isAnalysis: true,
    },
    {
      id: "workout",
      label: "Phân tích buổi tập vừa rồi",
      desc: "Splits, HR zone & cardiac drift",
      icon: Flame,
      color: "text-orange-400",
      isAnalysis: true,
    },
    {
      id: "rhr_recovery",
      label: "Đánh giá RHR & HRV phục hồi",
      desc: "Nhịp tim nghỉ ngơi & hồi phục",
      icon: Sparkles,
      color: "text-cyan-300",
      isAnalysis: false,
      text: "Đánh giá nhịp tim nghỉ ngơi (RHR) và độ phục hồi HRV của tôi đêm qua?",
    },
    {
      id: "injury_advice",
      label: "Tư vấn căng cơ & chấn thương",
      desc: "Chăm sóc cơ bắp sau chạy",
      icon: Bandage,
      color: "text-rose-400",
      isAnalysis: false,
      text: "Tôi bị mỏi bắp chuối sau buổi chạy hôm qua, hôm nay có nên chạy tiếp không?",
    },
  ];

  useEffect(() => {
    // Tải sẵn danh sách lịch sử để lưu vào Drawer Lịch sử (không đưa ra màn hình chính)
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

  // Bắt đầu một phiên chat mới hoàn toàn sạch sẽ
  const handleNewChat = () => {
    setMessages([]);
    setInput("");
    setError(null);
    setDrawerOpen(false);
  };

  // Mở lại toàn bộ lịch sử trò chuyện cũ từ Redis ra màn hình nếu người dùng muốn xem lại
  const handleRestoreHistory = () => {
    if (historyList.length > 0) {
      setMessages(historyList);
    }
    setDrawerOpen(false);
  };

  // Xem lại 1 tin nhắn cụ thể từ lịch sử
  const handleSelectHistoryItem = (item: ChatMessage) => {
    setMessages([
      { role: "user", content: item.content },
    ]);
    setDrawerOpen(false);
    // Tự động hỏi lại câu này để nhận phản hồi mới nhất
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

  return (
    <div className="flex flex-col flex-1 h-[calc(100dvh-3.25rem)] sm:h-[calc(100dvh-3.5rem)] max-w-3xl mx-auto w-full overflow-hidden">
      
      {/* KHUNG CHAT: Nếu chưa có tin nhắn, hiển thị màn hình New Chat tinh gọn */}
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 text-center overflow-y-auto">
          {/* Logo & Lời chào nhẹ nhàng */}
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20 mb-3">
            <Activity className="h-6 w-6" />
          </div>

          <h2 className="text-base sm:text-lg font-bold text-white mb-1 tracking-tight">
            Xin chào, {user?.name || "Vận động viên"}! 👋
          </h2>
          <p className="text-xs text-slate-400 max-w-xs sm:max-w-md mb-6 leading-relaxed">
            Tôi là HLV AI Garmin cá nhân của bạn. Hôm nay bạn muốn lên giáo án chạy, kiểm tra giấc ngủ hay phục hồi thể trạng?
          </p>

          {/* 4 Gợi ý kịch bản 1-chạm (Bố cục phẳng, thoáng mắt) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg text-left mb-4">
            {quickActionPrompts.slice(0, 4).map((p) => {
              const Icon = p.icon;
              return (
                <button
                  key={p.id}
                  onClick={() => handleTriggerAnalysis(p.id, p.label)}
                  disabled={loading}
                  className="p-3 rounded-xl border border-slate-800/80 bg-slate-900/60 hover:bg-slate-900 hover:border-cyan-500/40 transition flex items-center justify-between gap-3 group text-left"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 shrink-0">
                      <Icon className={`h-4 w-4 ${p.color}`} />
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-white group-hover:text-cyan-300 transition-colors">
                        {p.label}
                      </h4>
                      <p className="text-[11px] text-slate-400 mt-0.5">{p.desc}</p>
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-600 group-hover:text-cyan-400 transition shrink-0" />
                </button>
              );
            })}
          </div>

          {/* Nút xem lịch sử nếu có phiên cũ */}
          {historyList.length > 0 && (
            <button
              onClick={() => setDrawerOpen(true)}
              className="text-[11px] text-slate-400 hover:text-cyan-300 flex items-center gap-1.5 transition py-1"
            >
              <History className="h-3.5 w-3.5" />
              <span>Xem lại {historyList.length} câu hỏi trong lịch sử</span>
            </button>
          )}
        </div>
      ) : (
        /* DÒNG HỘI THOẠI KHI ĐANG CHAT */
        <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-4 space-y-4">
          {messages.map((m, idx) => {
            const isUser = m.role === "user";
            return (
              <div
                key={idx}
                className={`flex items-start gap-2.5 ${isUser ? "flex-row-reverse" : "flex-row"}`}
              >
                {/* Avatar */}
                <div
                  className={`flex h-7 w-7 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-xl text-xs font-bold ${
                    isUser
                      ? "bg-gradient-to-tr from-cyan-500 to-blue-600 text-white shadow-sm"
                      : "bg-slate-900 text-cyan-400 border border-slate-700/80"
                  }`}
                >
                  {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>

                {/* Bong bóng tin nhắn sạch sẽ */}
                <div
                  className={`max-w-[88%] sm:max-w-[82%] rounded-2xl p-3.5 sm:p-4 text-xs sm:text-sm leading-relaxed ${
                    isUser
                      ? "bg-cyan-600 text-white rounded-tr-xs shadow-sm font-medium"
                      : "bg-slate-900/90 text-slate-100 border border-slate-800/80 rounded-tl-xs space-y-3"
                  }`}
                >
                  {/* Header tin nhắn AI */}
                  {!isUser && (
                    <div className="flex items-center justify-between pb-2 border-b border-slate-800/70 text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-white tracking-tight">Garmin Coach</span>
                        <span className="rounded bg-cyan-950 px-1 py-0.2 text-[9px] font-semibold text-cyan-400 border border-cyan-800/50">AI</span>
                      </div>

                      <button
                        onClick={() => handleCopy(m.content, idx)}
                        title="Sao chép"
                        className="text-slate-400 hover:text-cyan-300 text-[10px] flex items-center gap-1 transition"
                      >
                        {copiedIdx === idx ? (
                          <>
                            <Check className="h-3 w-3 text-emerald-400" />
                            <span className="text-emerald-400">Đã chép</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" />
                            <span>Sao chép</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}

                  {/* Thẻ tóm tắt chỉ số thể trạng (nếu có metrics) */}
                  {m.metrics && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-2.5 rounded-xl bg-slate-950/80 border border-slate-800/80 text-xs">
                      {m.metrics.readiness_score !== undefined && m.metrics.readiness_score !== null && (
                        <div>
                          <span className="text-[10px] text-slate-400 block">Điểm sẵn sàng</span>
                          <span className="font-bold text-amber-400 text-sm">
                            {m.metrics.readiness_score}/100
                          </span>
                        </div>
                      )}
                      <div>
                        <span className="text-[10px] text-slate-400 block">Garmin Connect</span>
                        <span className={`font-semibold text-xs ${m.metrics.is_fresh ? "text-emerald-400" : "text-amber-400"}`}>
                          {m.metrics.is_fresh ? "Đã đồng bộ" : "Chờ đồng bộ"}
                        </span>
                      </div>
                      {m.metrics.date && (
                        <div>
                          <span className="text-[10px] text-slate-400 block">Ngày phân tích</span>
                          <span className="font-medium text-white text-xs">{m.metrics.date}</span>
                        </div>
                      )}
                      {m.mode && (
                        <div>
                          <span className="text-[10px] text-slate-400 block">Chế độ</span>
                          <span className="font-bold text-cyan-400 uppercase text-xs">{m.mode}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Nội dung phản hồi: Văn bản tự nhiên, không đóng hộp */}
                  {isUser ? (
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  ) : (
                    <MarkdownRenderer content={m.content} />
                  )}

                  {/* Trình phát âm thanh nếu có */}
                  {m.audio_url && (
                    <div className="pt-2 border-t border-slate-800/80">
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
              <div className="flex h-7 w-7 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-cyan-400 border border-slate-700">
                <Bot className="h-4 w-4" />
              </div>
              <div className="rounded-2xl rounded-tl-xs border border-slate-800 bg-slate-900/90 p-3 sm:p-3.5 text-xs text-slate-300 flex items-center gap-2">
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
                <span>HLV AI đang tra cứu dữ liệu Garmin và trả lời...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Thông báo lỗi */}
      {error && (
        <div className="mx-3 mb-2 p-2.5 rounded-xl border border-red-800 bg-red-950/60 text-xs text-red-300 flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center gap-1.5">
            <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-white p-1">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Ô NHẬP LIỆU DÍNH ĐÁY */}
      <div className="p-2.5 sm:p-3 border-t border-slate-900 bg-slate-950/95 shrink-0 z-20">
        <div className="flex items-end gap-2 bg-slate-900/90 border border-slate-800 rounded-2xl px-3 py-1.5 focus-within:border-cyan-500 transition shadow-lg">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Hỏi HLV AI điều gì đó..."
            rows={1}
            className="w-full resize-none bg-transparent py-1.5 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none max-h-28"
          />

          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="flex h-8.5 w-8.5 items-center justify-center rounded-xl bg-cyan-500 text-slate-950 hover:bg-cyan-400 disabled:opacity-30 transition shrink-0 mb-0.5"
            title="Gửi câu hỏi"
          >
            <Send className="h-4 w-4 fill-slate-950 text-slate-950" />
          </button>
        </div>
      </div>

      {/* DRAWER LỊCH SỬ HỘI THOẠI (Lưu trữ các câu trả lời cũ) */}
      {drawerOpen && (
        <>
          <div
            onClick={() => setDrawerOpen(false)}
            className="fixed inset-0 bg-black/60 z-40 backdrop-blur-xs transition-opacity"
          />
          <div className="fixed inset-y-0 left-0 w-80 max-w-[85vw] bg-slate-950 border-r border-slate-800 z-50 p-4 flex flex-col shadow-2xl animate-in slide-in-from-left duration-200">
            {/* Header Drawer */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-cyan-400" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Lịch sử Hội thoại</h3>
              </div>
              <button
                onClick={() => setDrawerOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Nút bắt đầu Chat Mới */}
            <button
              onClick={handleNewChat}
              className="flex items-center justify-center gap-1.5 w-full py-2 px-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs mb-3 transition shadow-sm"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Bắt đầu cuộc trò chuyện mới</span>
            </button>

            {/* Danh sách các câu hỏi cũ trong lịch sử */}
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 text-xs">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Các câu hỏi gần đây ({historyList.filter(h => h.role === "user").length})
              </div>

              {historyList.length === 0 ? (
                <div className="p-4 text-center text-slate-500 text-xs">
                  Chưa có lịch sử hội thoại nào được lưu.
                </div>
              ) : (
                historyList
                  .filter((item) => item.role === "user")
                  .map((item, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleSelectHistoryItem(item)}
                      className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-cyan-500/40 text-slate-200 cursor-pointer hover:bg-slate-800 transition flex items-center justify-between gap-2"
                    >
                      <div className="flex items-center gap-2 truncate flex-1">
                        <MessageSquare className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                        <span className="truncate">{item.content}</span>
                      </div>
                      <ChevronRight className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                    </div>
                  ))
              )}

              {/* Nút xem lại toàn bộ phiên cũ nếu muốn */}
              {historyList.length > 0 && (
                <div className="pt-3 border-t border-slate-800/80">
                  <button
                    onClick={handleRestoreHistory}
                    className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg border border-slate-800 text-[11px] text-slate-300 hover:text-white hover:bg-slate-900 transition"
                  >
                    <span>Mở lại toàn bộ phiên trước</span>
                  </button>
                </div>
              )}
            </div>

            {/* Thông tin nhanh hồ sơ */}
            <div className="pt-2.5 border-t border-slate-800 text-[11px] text-slate-400 space-y-1">
              <div className="flex items-center gap-1.5 text-slate-300">
                <Target className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                <span className="truncate">{user?.goal || "Chạy bộ"}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
