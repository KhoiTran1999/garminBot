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
    <div className="max-w-2xl mx-auto space-y-6 px-4 sm:px-6 py-6">
      {/* Header Material Design 3 Light */}
      <div className="flex items-center gap-3.5 border-b border-slate-200 pb-5">
        <div className="p-3 rounded-2xl bg-sky-100 text-sky-700 shrink-0">
          <User className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">Hồ sơ Vận động viên & Ngữ cảnh AI</h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-0.5">
            Dữ liệu được lưu trữ và đồng bộ hóa trực tiếp 2 chiều với Notion Database của bạn
          </p>
        </div>
      </div>

      {successMsg && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-800 flex items-center gap-3 shadow-xs">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
          <span className="font-medium">{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-xs text-red-700 flex items-center gap-3 shadow-xs">
          <AlertCircle className="h-4 w-4 text-red-600 shrink-0" />
          <span className="font-medium">{errorMsg}</span>
        </div>
      )}

      {/* Account Info card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs">
        <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
          <Database className="h-4 w-4 text-sky-600" />
          <span>Thông tin Tài khoản Notion</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-slate-500 block mb-1 font-medium">Tên Vận động viên</span>
            <span className="font-semibold text-slate-900 text-sm">{user?.name || "..."}</span>
          </div>
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-slate-500 block mb-1 font-medium">Email Garmin kết nối</span>
            <span className="font-semibold text-slate-900 text-sm">{user?.email || "..."}</span>
          </div>
        </div>
      </div>

      {/* Editable form card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs">
        <h2 className="text-sm font-bold text-slate-900 mb-4">
          Tùy chỉnh Ngữ cảnh Huấn luyện
        </h2>

        <form onSubmit={handleSave} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-900 mb-2 flex items-center gap-2">
              <Target className="h-4 w-4 text-sky-600" />
              Mục tiêu Tập luyện (Training Goal)
            </label>
            <input
              type="text"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="VD: Marathon Sub 3:30, Chạy 10km dưỡng sinh, HM Sub 1:45..."
              className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 transition"
            />
            <p className="mt-1.5 text-[11px] text-slate-500">
              AI sẽ dựa vào mục tiêu này để tính toán pace chạy bài Tempo, Interval hoặc Long Run.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-900 mb-2 flex items-center gap-2">
              <Bandage className="h-4 w-4 text-rose-600" />
              Chấn thương & Tình trạng Bệnh tật (Injury & Health)
            </label>
            <input
              type="text"
              value={injury}
              onChange={(e) => setInjury(e.target.value)}
              placeholder="VD: Đau gót chân phải, Đang hồi phục sau cảm cúm, Không có..."
              className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-rose-500 focus:outline-none focus:ring-1 focus:ring-rose-500 transition"
            />
            <p className="mt-1.5 text-[11px] text-slate-500">
              Nếu có chấn thương, AI sẽ tự động cảnh báo giảm khối lượng hoặc chuyển sang bài phục hồi.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-900 mb-2 flex items-center gap-2">
              <FileText className="h-4 w-4 text-amber-600" />
              Ghi chú thêm cho Huấn luyện viên AI
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder="VD: Chỉ có thể chạy vào các buổi sáng sớm thứ 3, 5, 7 và Chủ nhật..."
              className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 transition"
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 rounded-full bg-sky-600 hover:bg-sky-500 py-3 text-xs sm:text-sm font-medium text-white shadow-xs hover:shadow transition disabled:opacity-50 active:scale-[0.99]"
          >
            {saving ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
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
