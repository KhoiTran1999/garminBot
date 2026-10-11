"use client";

import React from "react";
import ReactMarkdown, { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { 
  Activity, 
  Heart, 
  Flame, 
  BatteryCharging, 
  Sparkles, 
  Clock, 
  Footprints,
  Compass
} from "lucide-react";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

// Hàm trích xuất text thuần từ React children để nhận biết chỉ số
function extractText(node: any): string {
  if (!node) return "";
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (node.props && node.props.children) return extractText(node.props.children);
  return "";
}

// Nhận diện loại chỉ số sức khỏe/bài tập
function getMetricType(text: string) {
  const t = text.toLowerCase();
  if (t.includes("quãng đường") || t.includes("cự ly") || t.includes("km")) {
    return { icon: Compass, color: "text-cyan-400", bg: "bg-cyan-500/10 border-cyan-500/20" };
  }
  if (t.includes("thời lượng") || t.includes("thời gian") || t.includes("phút")) {
    return { icon: Clock, color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" };
  }
  if (t.includes("nhịp tim") || t.includes("bpm") || t.includes("hr") || t.includes("rhr")) {
    return { icon: Heart, color: "text-rose-400", bg: "bg-rose-500/10 border-rose-500/20" };
  }
  if (t.includes("calo") || t.includes("kcal") || t.includes("tiêu hao")) {
    return { icon: Flame, color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" };
  }
  if (t.includes("pin cơ thể") || t.includes("body battery") || t.includes("pin")) {
    return { icon: BatteryCharging, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" };
  }
  if (t.includes("căng thẳng") || t.includes("stress")) {
    return { icon: Activity, color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20" };
  }
  if (t.includes("bước chân") || t.includes("bước")) {
    return { icon: Footprints, color: "text-teal-400", bg: "bg-teal-500/10 border-teal-500/20" };
  }
  return null;
}

const customComponents: Components = {
  h1: ({ children }) => (
    <div className="mt-5 mb-3 pb-2 border-b border-slate-800">
      <h1 className="text-base sm:text-lg font-extrabold text-white tracking-tight flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-cyan-400" />
        <span>{children}</span>
      </h1>
    </div>
  ),
  h2: ({ children }) => (
    <div className="mt-4 mb-2.5 pb-1.5 border-b border-slate-800/80 flex items-center gap-2">
      <div className="h-5 w-5 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 flex items-center justify-center shrink-0">
        <Activity className="h-3 w-3" />
      </div>
      <h2 className="text-sm sm:text-base font-bold text-white tracking-tight">
        {children}
      </h2>
    </div>
  ),
  h3: ({ children }) => (
    <div className="mt-3.5 mb-2 flex items-center gap-2">
      <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shrink-0" />
      <h3 className="text-xs sm:text-sm font-bold text-cyan-300 tracking-tight">
        {children}
      </h3>
    </div>
  ),
  h4: ({ children }) => (
    <h4 className="text-xs sm:text-sm font-semibold text-slate-200 mt-2 mb-1">
      {children}
    </h4>
  ),
  p: ({ children }) => (
    <p className="mb-2 last:mb-0 leading-relaxed text-slate-300 text-xs sm:text-sm">
      {children}
    </p>
  ),
  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
  em: ({ children }) => <em className="italic text-slate-300">{children}</em>,
  hr: () => <hr className="my-3 border-slate-800/80" />,
  ul: ({ children }) => (
    <ul className="space-y-1.5 my-2 pl-0 list-none text-slate-200">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="space-y-1.5 my-2 pl-0 list-none text-slate-200">
      {children}
    </ol>
  ),
  li: ({ children }) => {
    const rawText = extractText(children);
    const metric = getMetricType(rawText);

    // Nếu là chỉ số thể thao / sức khỏe: Hiển thị dạng Stat Card đẹp mắt
    if (metric) {
      const Icon = metric.icon;
      return (
        <li className="list-none my-1.5">
          <div className="flex items-start gap-2.5 p-2 sm:p-2.5 rounded-xl bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 transition">
            <div className={`p-1.5 rounded-lg border shrink-0 mt-0.5 ${metric.bg} ${metric.color}`}>
              <Icon className="h-3.5 w-3.5" />
            </div>
            <div className="flex-1 text-xs sm:text-sm leading-relaxed text-slate-200">
              {children}
            </div>
          </div>
        </li>
      );
    }

    // List item thông thường: Bullet tinh tế, không thụt lề thô kệch
    return (
      <li className="list-none my-1.5 flex items-start gap-2 text-xs sm:text-sm leading-relaxed text-slate-200">
        <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 mt-2 shrink-0" />
        <div className="flex-1 leading-relaxed">{children}</div>
      </li>
    );
  },
  code: ({ children, className: codeClassName }) => {
    const isInline = !codeClassName;
    return isInline ? (
      <code className="rounded bg-slate-800/90 px-1.5 py-0.5 font-mono text-[11px] text-cyan-300 border border-slate-700/50">
        {children}
      </code>
    ) : (
      <pre className="overflow-x-auto rounded-xl bg-slate-950 p-3 my-2 border border-slate-800 font-mono text-xs text-slate-300">
        <code>{children}</code>
      </pre>
    );
  },
  blockquote: ({ children }) => (
    <blockquote className="my-2.5 rounded-xl border border-cyan-500/30 bg-gradient-to-r from-cyan-950/30 to-slate-950/40 p-3 text-xs sm:text-sm text-cyan-200">
      <div className="flex items-start gap-2">
        <Sparkles className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
        <div className="flex-1 leading-relaxed">{children}</div>
      </div>
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-2.5 rounded-xl border border-slate-800">
      <table className="w-full text-left text-xs border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-slate-800/80 text-white font-semibold">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-slate-800/50">{children}</tbody>,
  tr: ({ children }) => <tr className="hover:bg-slate-800/30 transition">{children}</tr>,
  th: ({ children }) => <th className="px-3 py-2 border-b border-slate-700">{children}</th>,
  td: ({ children }) => <td className="px-3 py-2 text-slate-300">{children}</td>,
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className = "",
}) => {
  // Chuẩn hóa nội dung trước khi render:
  // 1. Chuyển các đầu mục số dạng "* 1. Tiêu đề" hoặc "• 2. Tiêu đề" thành Heading H2/H3
  let normalized = content ? content.replace(/^[ \t]*[•●\*\-][ \t]+(\d+\.\s+[^\n]+)$/gm, "\n## $1\n") : "";
  // 2. Chuyển các đầu bullet unicode • hoặc ● sang markdown -
  normalized = normalized.replace(/^[ \t]*[•●][ \t]*/gm, "- ");

  return (
    <div className={`markdown-body space-y-2 leading-relaxed text-xs sm:text-sm text-slate-200 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={customComponents}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  );
};
