"use client";

import React from "react";
import ReactMarkdown, { Components } from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

const customComponents: Components = {
  h1: ({ children }) => (
    <h1 className="text-base sm:text-lg font-bold text-white mt-4 mb-2 pb-1 border-b border-slate-800">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-sm sm:text-base font-bold text-cyan-400 mt-4 mb-2 flex items-center gap-1.5">
      <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shrink-0" />
      <span>{children}</span>
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-xs sm:text-sm font-semibold text-sky-300 mt-3 mb-1.5">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="mb-2.5 last:mb-0 leading-relaxed text-slate-200 text-xs sm:text-sm">
      {children}
    </p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-white">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-slate-300">{children}</em>
  ),
  hr: () => <hr className="my-3 border-slate-800/80" />,
  ul: ({ children }) => (
    <ul className="list-disc list-outside ml-4 space-y-1.5 my-2 text-slate-300 text-xs sm:text-sm">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside ml-4 space-y-1.5 my-2 text-slate-300 text-xs sm:text-sm">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="leading-relaxed pl-1 marker:text-cyan-400">
      {children}
    </li>
  ),
  code: ({ children, className: codeClassName }) => {
    const isInline = !codeClassName;
    return isInline ? (
      <code className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[11px] text-cyan-300 border border-slate-700/50">
        {children}
      </code>
    ) : (
      <pre className="overflow-x-auto rounded-xl bg-slate-950 p-3 my-2 border border-slate-800 font-mono text-xs text-slate-300">
        <code>{children}</code>
      </pre>
    );
  },
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-cyan-500/70 pl-3 my-2 text-slate-300 italic bg-cyan-950/20 py-1.5 rounded-r text-xs sm:text-sm">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-3 rounded-xl border border-slate-800">
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
  // Chuẩn hóa markdown:
  // Chuyển các đầu mục "* 1. ", "* 2. " thành "### 1. ", "### 2. " để không bị lồng vào bullet point
  let normalized = content ? content.replace(/^[ \t]*[•●\*\-][ \t]+(\d+\.\s+[^\n]+)$/gm, "\n## $1\n") : "";
  // Chuyển các unicode bullets •, ● thành markdown chuẩn -
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
