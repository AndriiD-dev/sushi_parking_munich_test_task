/**
 * Individual chat message bubble.
 *
 * Renders user and assistant messages with distinct styling.
 * Assistant messages support basic text formatting (the content comes
 * from the LLM as plain text with markdown-like patterns).
 */

import type { ChatMessage } from "../lib/types";

interface ChatMessageItemProps {
  message: ChatMessage;
}

/**
 * Parse assistant text to simple React-safe elements.
 *
 * Handles bold (**text**), inline code (`code`), and preserves newlines.
 * Does NOT use dangerouslySetInnerHTML — all output is React elements.
 */
function formatAssistantContent(content: string): React.ReactNode[] {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];

  for (let i = 0; i < lines.length; i++) {
    if (i > 0) {
      elements.push(<br key={`br-${i}`} />);
    }

    const line = lines[i];
    // Split on bold (**text**), code (`text`), and links ([text](url)) patterns
    const parts = line.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g);

    for (let j = 0; j < parts.length; j++) {
      const part = parts[j];
      if (part.startsWith("**") && part.endsWith("**")) {
        elements.push(
          <strong key={`${i}-${j}`}>{part.slice(2, -2)}</strong>,
        );
      } else if (part.startsWith("`") && part.endsWith("`")) {
        elements.push(<code key={`${i}-${j}`}>{part.slice(1, -1)}</code>);
      } else if (part.startsWith("[") && part.includes("](")) {
        const linkText = part.match(/\[(.*?)\]/)?.[1] || "";
        const linkUrl = part.match(/\((.*?)\)/)?.[1] || "";
        elements.push(
          <a
            key={`${i}-${j}`}
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="message-link"
          >
            {linkText}
          </a>,
        );
      } else {
        elements.push(part);
      }
    }
  }

  return elements;
}

export default function ChatMessageItem({ message }: ChatMessageItemProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`message-item ${isUser ? "message-item--user" : "message-item--assistant"}`}
    >
      <div className="message-label">{isUser ? "You" : "Assistant"}</div>
      <div
        className={`message-bubble ${isUser ? "message-bubble--user" : "message-bubble--assistant"}`}
      >
        {isUser ? message.content : formatAssistantContent(message.content)}
      </div>
    </div>
  );
}
