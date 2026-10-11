"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { User, Target, Bandage, FileText, Save, CheckCircle2, AlertCircle, Database } from "lucide-react";

export default function ProfilePage() {
  const { user, refreshProfile } = useAuth();
  const [goal, setGoal] = useState("");
  const [injury, setInjury] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setGoal(user.goal || "");
      setInjury(user.injury || "");
      setNote(user.note || "");
    }
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      const res = await api.updateProfile({ goal, injury, note });
      setSuccessMsg(res.message || "Cập nhật thành công lên Notion Database!");
      await refreshProfile();
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setErrorMsg(err.message || "Lỗi đồng bộ Notion. Vui lòng thử lại.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3 border-b border-slate-800 pb-5">
        <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
          <User className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Hồ sơ Vận động viên & Ngữ cảnh AI</h1>
          <p className="text-xs text-slate-400">
            Dữ liệu được lưu trữ và đồng bộ hóa trực tiếp 2 chiều với Notion Database của bạn
          </p>
        </div>
      </div>

      {successMsg && (
        <div className="rounded-xl border border-emerald-800 bg-emerald-950/40 p-4 text-xs text-emerald-300 flex items-center gap-3">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-xs text-red-300 flex items-center gap-3">
          <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Account Info card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl">
        <h2 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
          <Database className="h-4 w-4 text-cyan-400" />
          <span>Thông tin Tài khoản Notion</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-slate-500 block mb-1">Tên Vận động viên</span>
            <span className="font-semibold text-white text-sm">{user?.name || "..."}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-slate-500 block mb-1">Email Garmin kết nối</span>
            <span className="font-semibold text-white text-sm">{user?.email || "..."}</span>
          </div>
        </div>
      </div>

      {/* Editable form card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl">
        <h2 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
          <span>Tùy chỉnh Ngữ cảnh Huấn luyện</span>
        </h2>

        <form onSubmit={handleSave} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <Target className="h-4 w-4 text-cyan-400" />
              Mục tiêu Tập luyện (Training Goal)
            </label>
            <input
              type="text"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="VD: Marathon Sub 3:30, Chạy 10km dưỡng sinh, HM Sub 1:45..."
              className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
            />
            <p className="mt-1 text-[11px] text-slate-500">
              AI sẽ dựa vào mục tiêu này để tính toán pace chạy bài Tempo, Interval hoặc Long Run.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <Bandage className="h-4 w-4 text-rose-400" />
              Chấn thương & Tình trạng Bệnh tật (Injury & Health)
            </label>
            <input
              type="text"
              value={injury}
              onChange={(e) => setInjury(e.target.value)}
              placeholder="VD: Đau gót chân phải, Đang hồi phục sau cảm cúm, Không có..."
              className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-rose-500 focus:outline-none"
            />
            <p className="mt-1 text-[11px] text-slate-500">
              Nếu có chấn thương, AI sẽ tự động cảnh báo giảm khối lượng hoặc chuyển sang bài phục hồi.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <FileText className="h-4 w-4 text-amber-400" />
              Ghi chú thêm cho Huấn luyện viên AI
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder="VD: Chỉ có thể chạy vào các buổi sáng sớm thứ 3, 5, 7 và Chủ nhật..."
              className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 py-3 text-xs font-bold text-slate-950 shadow-lg shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 transition disabled:opacity-50"
          >
            {saving ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
                <span>Đang đồng bộ lên Notion...</span>
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                <span>Lưu & Đồng bộ lên Notion Database</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
