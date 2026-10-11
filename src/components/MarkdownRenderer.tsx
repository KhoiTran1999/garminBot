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
    <h1 className="text-lg md:text-xl font-bold text-white mt-4 mb-2 pb-1 border-b border-slate-800">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-base md:text-lg font-bold text-cyan-300 mt-4 mb-2 flex items-center gap-2">
      <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm md:text-base font-semibold text-cyan-400 mt-3 mb-1.5 flex items-center gap-2">
      <span className="h-1.5 w-1.5 rounded-full bg-cyan-400/80" />
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-xs md:text-sm font-semibold text-sky-300 mt-2.5 mb-1">
      {children}
    </h4>
  ),
  p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
  em: ({ children }) => <em className="italic text-slate-300">{children}</em>,
  hr: () => <hr className="my-3.5 border-slate-800" />,
  ul: ({ children }) => (
    <ul className="list-disc list-outside ml-4 md:ml-5 space-y-1.5 my-2 text-slate-300">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside ml-4 md:ml-5 space-y-1.5 my-2 text-slate-300">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="leading-relaxed pl-1 marker:text-cyan-400/80">{children}</li>
  ),
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
    <blockquote className="border-l-2 border-cyan-500/60 pl-3 my-2 text-slate-400 italic bg-cyan-950/10 py-1 rounded-r">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-3 rounded-lg border border-slate-800">
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
  // Normalize bullet points (convert unicode bullets • or ● to markdown list -)
  const normalizedContent = content
    ? content.replace(/^[ \t]*[•●][ \t]*/gm, "- ")
    : "";

  return (
    <div className={`markdown-body space-y-2.5 leading-relaxed text-xs md:text-sm text-slate-200 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={customComponents}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
};
