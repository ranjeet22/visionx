import React from 'react';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export const MarkdownContent: React.FC<MarkdownContentProps> = ({ content, className = '' }) => {
  if (!content) return null;

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];

  let currentList: { type: 'ul' | 'ol'; items: React.ReactNode[] } | null = null;
  let codeBlockLines: string[] | null = null;
  let codeBlockLang = '';

  const flushList = () => {
    if (currentList) {
      if (currentList.type === 'ul') {
        elements.push(
          <ul key={`ul-${elements.length}`} className="markdown-ul">
            {currentList.items.map((it, idx) => (
              <li key={idx} className="markdown-li">
                {it}
              </li>
            ))}
          </ul>
        );
      } else {
        elements.push(
          <ol key={`ol-${elements.length}`} className="markdown-ol">
            {currentList.items.map((it, idx) => (
              <li key={idx} className="markdown-li">
                {it}
              </li>
            ))}
          </ol>
        );
      }
      currentList = null;
    }
  };

  // Helper to parse inline markdown: bold, italic, inline code, links
  const parseInline = (text: string): React.ReactNode => {
    // Regex matches ***bold italic***, ___bold italic___, **bold**, __bold__, *italic*, _italic_, `code`, [label](url)
    const tokenRegex = /(\*\*\*[\s\S]+?\*\*\*|___[\s\S]+?___|\*\*[\s\S]+?\*\*|__[\s\S]+?__|(?<!\w)\*[\s\S]+?\*(?!\w)|(?<!\w)_[\s\S]+?_(?!\w)|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
    const parts = text.split(tokenRegex);

    return parts.map((part, i) => {
      if (!part) return null;

      // Bold + Italic: *** or ___
      if ((part.startsWith('***') && part.endsWith('***') && part.length >= 6) ||
          (part.startsWith('___') && part.endsWith('___') && part.length >= 6)) {
        return (
          <strong key={i}>
            <em>{part.slice(3, -3)}</em>
          </strong>
        );
      }
      // Bold: ** or __
      if ((part.startsWith('**') && part.endsWith('**') && part.length >= 4) ||
          (part.startsWith('__') && part.endsWith('__') && part.length >= 4)) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      // Italic: * or _
      if ((part.startsWith('*') && part.endsWith('*') && part.length >= 2) ||
          (part.startsWith('_') && part.endsWith('_') && part.length >= 2)) {
        return <em key={i}>{part.slice(1, -1)}</em>;
      }
      // Inline Code: `
      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        return (
          <code key={i} className="markdown-inline-code">
            {part.slice(1, -1)}
          </code>
        );
      }
      // Link: [text](url)
      const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        return (
          <a
            key={i}
            href={linkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="markdown-link"
          >
            {linkMatch[1]}
          </a>
        );
      }

      return part;
    });
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // Check for fenced code block toggle: ```lang
    if (trimmed.startsWith('```')) {
      flushList();
      if (codeBlockLines !== null) {
        // Closing fence
        elements.push(
          <pre key={`code-${i}`} className="markdown-pre" data-language={codeBlockLang}>
            <code className="markdown-code-block">{codeBlockLines.join('\n')}</code>
          </pre>
        );
        codeBlockLines = null;
        codeBlockLang = '';
      } else {
        // Opening fence
        codeBlockLang = trimmed.slice(3).trim();
        codeBlockLines = [];
      }
      continue;
    }

    // Inside a fenced code block
    if (codeBlockLines !== null) {
      codeBlockLines.push(rawLine);
      continue;
    }

    // Empty lines flush active lists
    if (!trimmed) {
      flushList();
      continue;
    }

    // Horizontal Rule: ---, ***, ___ (at least 3 characters)
    if (/^(?:[-*_]){3,}$/.test(trimmed)) {
      flushList();
      elements.push(<hr key={`hr-${i}`} className="markdown-hr" />);
      continue;
    }

    // Heading: # up to ######
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      flushList();
      const level = headingMatch[1].length;
      const headingText = headingMatch[2];
      const parsedHeading = parseInline(headingText);

      if (level === 1 || level === 2) {
        elements.push(
          <h3 key={`h-${i}`} className="markdown-h3">
            {parsedHeading}
          </h3>
        );
      } else {
        elements.push(
          <h4 key={`h-${i}`} className="markdown-h4">
            {parsedHeading}
          </h4>
        );
      }
      continue;
    }

    // Bullet List item: - or * or + or •
    const bulletMatch = trimmed.match(/^[-*+•]\s+(.*)$/);
    if (bulletMatch) {
      if (!currentList || currentList.type !== 'ul') {
        flushList();
        currentList = { type: 'ul', items: [] };
      }
      currentList.items.push(parseInline(bulletMatch[1]));
      continue;
    }

    // Numbered List item: 1. or 2.
    const numMatch = trimmed.match(/^\d+\.\s+(.*)$/);
    if (numMatch) {
      if (!currentList || currentList.type !== 'ol') {
        flushList();
        currentList = { type: 'ol', items: [] };
      }
      currentList.items.push(parseInline(numMatch[1]));
      continue;
    }

    // Blockquote: >
    const quoteMatch = trimmed.match(/^>\s*(.*)$/);
    if (quoteMatch) {
      flushList();
      elements.push(
        <blockquote key={`quote-${i}`} className="markdown-blockquote">
          {parseInline(quoteMatch[1])}
        </blockquote>
      );
      continue;
    }

    // Standard Paragraph
    flushList();
    elements.push(
      <p key={`p-${i}`} className="markdown-p">
        {parseInline(trimmed)}
      </p>
    );
  }

  // Flush any dangling list or code block
  flushList();
  if (codeBlockLines !== null) {
    elements.push(
      <pre key={`code-end`} className="markdown-pre" data-language={codeBlockLang}>
        <code className="markdown-code-block">{codeBlockLines.join('\n')}</code>
      </pre>
    );
  }

  return <div className={`markdown-body-container ${className}`}>{elements}</div>;
};
