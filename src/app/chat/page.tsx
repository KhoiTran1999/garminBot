"use client";

import React, { useState, useEffect, useRef } from "react";
import { api, ChatMessage } from "@/lib/api";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { MessageSquare, Send, Sparkles, User, Bot, AlertCircle, RefreshCw } from "lucide-react";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetchingHistory, setFetchingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const suggestedPrompts = [
    "Hôm nay thể trạng của tôi nên chạy bài gì?",
    "Đánh giá nhịp tim nghỉ ngơi (RHR) và độ phục hồi của tôi đêm qua?",
    "Tôi bị căng cơ đùi sau nhẹ sau buổi tập hôm qua, có nên chạy tiếp không?",
    "Giải thích chỉ số Acute Training Load (TRIMP) 7 ngày qua của tôi?",
  ];

  useEffect(() => {
    loadChatHistory();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const loadChatHistory = async () => {
    setFetchingHistory(true);
    try {
      const res = await api.getChatHistory();
      if (res.history && res.history.length > 0) {
        setMessages(res.history);
      } else {
        // Welcome message
        setMessages([
          {
            role: "assistant",
            content: "Xin chào! Tôi là Garmin AI Coach của bạn. Bạn có thể hỏi tôi bất kỳ điều gì về bài tập, giấc ngủ, chấn thương, hoặc nhờ tôi tra cứu các chỉ số sức khỏe trực tiếp từ đồng hồ Garmin của bạn.",
          },
        ]);
      }
    } catch (err) {
      console.error("Load chat error:", err);
    } finally {
      setFetchingHistory(false);
    }
  };

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || loading) return;

    setError(null);
    setInput("");
    const newMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, newMsg]);

    setLoading(true);
    try {
      const res = await api.sendChatMessage(text);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
    } catch (err: any) {
      setError(err.message || "Lỗi gửi câu hỏi. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="max-w-4xl mx-auto flex flex-col h-[calc(100vh-8.5rem)]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <MessageSquare className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              <span>Phòng Chat Trực tiếp với HLV AI</span>
              <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            </h1>
            <p className="text-xs text-slate-400">
              Trợ lý AI hỗ trợ Tool Calling tra cứu trực tiếp dữ liệu nhịp tim, giấc ngủ và bài tập từ Garmin
            </p>
          </div>
        </div>

        <button
          onClick={loadChatHistory}
          title="Tải lại lịch sử hội thoại"
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-900 hover:text-white border border-slate-800 transition"
        >
          <RefreshCw className={`h-4 w-4 ${fetchingHistory ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Suggested Prompts if short history */}
      {messages.length <= 2 && (
        <div className="py-3 shrink-0">
          <p className="text-[11px] font-semibold text-slate-400 mb-2 flex items-center gap-1.5">
            <Sparkles className="h-3 w-3 text-cyan-400" />
            Câu hỏi gợi ý nhanh:
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestedPrompts.map((p, i) => (
              <button
                key={i}
                onClick={() => handleSend(p)}
                className="rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-300 hover:border-cyan-500/50 hover:text-cyan-300 transition text-left"
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
        {messages.map((m, idx) => {
          const isUser = m.role === "user";
          return (
            <div
              key={idx}
              className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
            >
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-xs font-bold ${
                  isUser
                    ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                    : "bg-slate-800 text-cyan-400 border border-slate-700"
                }`}
              >
                {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>

              <div
                className={`max-w-[85%] rounded-2xl p-4 text-xs md:text-sm leading-relaxed ${
                  isUser
                    ? "bg-cyan-600 text-white rounded-tr-none shadow-lg"
                    : "bg-slate-900/90 text-slate-200 border border-slate-800 rounded-tl-none shadow-md"
                }`}
              >
                {isUser ? (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                ) : (
                  <MarkdownRenderer content={m.content} />
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-cyan-400 border border-slate-700">
              <Bot className="h-4 w-4" />
            </div>
            <div className="rounded-2xl rounded-tl-none border border-slate-800 bg-slate-900/90 p-4 text-xs text-slate-400 flex items-center gap-2">
              <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
              <span>HLV AI đang tra cứu dữ liệu Garmin và phản hồi...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="mb-2 p-2.5 rounded-lg border border-red-800 bg-red-950/40 text-xs text-red-300 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Input box */}
      <div className="pt-2 border-t border-slate-800 shrink-0">
        <div className="relative flex items-end rounded-2xl border border-slate-800 bg-slate-900/90 p-2 shadow-xl focus-within:border-cyan-500">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nhập câu hỏi của bạn về giáo án, bài tập, dinh dưỡng hoặc chấn thương... (Nhấn Enter để gửi)"
            rows={2}
            className="w-full resize-none bg-transparent px-3 py-1.5 text-xs md:text-sm text-white placeholder-slate-500 focus:outline-none"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-cyan-500 text-slate-950 hover:bg-cyan-400 disabled:opacity-40 transition shadow-md shadow-cyan-500/20"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-1.5 text-[10px] text-slate-500 text-center">
          Nhấn Enter để gửi tin nhắn, Shift + Enter để xuống dòng.
        </p>
      </div>
    </div>
  );
}
