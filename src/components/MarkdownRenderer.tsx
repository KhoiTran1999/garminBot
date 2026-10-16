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
    <h1 className="text-base sm:text-lg font-bold text-slate-900 mt-4 mb-2 pb-1.5 border-b border-slate-200">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-sm sm:text-base font-bold text-sky-700 mt-4 mb-2 flex items-center gap-2">
      <span className="h-2 w-2 rounded-full bg-sky-600 shrink-0" />
      <span>{children}</span>
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-xs sm:text-sm font-semibold text-indigo-700 mt-3 mb-1.5">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="mb-2.5 last:mb-0 leading-relaxed text-slate-700 text-xs sm:text-sm">
      {children}
    </p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-slate-600">{children}</em>
  ),
  hr: () => <hr className="my-3 border-slate-200" />,
  ul: ({ children }) => (
    <ul className="list-disc list-outside ml-4 space-y-1.5 my-2 text-slate-700 text-xs sm:text-sm">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside ml-4 space-y-1.5 my-2 text-slate-700 text-xs sm:text-sm">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="leading-relaxed pl-1 marker:text-sky-600">
      {children}
    </li>
  ),
  code: ({ children, className: codeClassName }) => {
    const isInline = !codeClassName;
    return isInline ? (
      <code className="rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-sky-800 border border-slate-200">
        {children}
      </code>
    ) : (
      <pre className="overflow-x-auto rounded-xl bg-slate-900 p-3.5 my-2 border border-slate-800 font-mono text-xs text-slate-100">
        <code>{children}</code>
      </pre>
    );
  },
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-sky-600 pl-3.5 my-2.5 text-slate-700 italic bg-sky-50 py-2 rounded-r-xl text-xs sm:text-sm">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-3 rounded-xl border border-slate-200 bg-white shadow-2xs">
      <table className="w-full text-left text-xs border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-slate-50 text-slate-900 font-semibold">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-slate-100">{children}</tbody>,
  tr: ({ children }) => <tr className="hover:bg-slate-50/70 transition">{children}</tr>,
  th: ({ children }) => <th className="px-3.5 py-2.5 border-b border-slate-200 font-semibold">{children}</th>,
  td: ({ children }) => <td className="px-3.5 py-2 text-slate-700">{children}</td>,
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className = "",
}) => {
  let normalized = content ? content.replace(/^[ \t]*[•●\*\-][ \t]+(\d+\.\s+[^\n]+)$/gm, "\n## $1\n") : "";
  normalized = normalized.replace(/^[ \t]*[•●][ \t]*/gm, "- ");

  return (
    <div className={`markdown-body space-y-2 leading-relaxed text-xs sm:text-sm text-slate-800 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={customComponents}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  );
};
