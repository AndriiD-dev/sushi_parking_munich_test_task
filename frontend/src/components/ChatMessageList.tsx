/**
 * Scrollable message list with auto-scroll and empty state.
 */

import { useEffect, useRef } from "react";
import type { ChatMessage } from "../lib/types";
import ChatMessageItem from "./ChatMessageItem";

interface ChatMessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export default function ChatMessageList({
  messages,
  isLoading,
}: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="message-list">
        <div className="empty-state">
          <div className="empty-state__icon">🍣</div>
          <div className="empty-state__title">
            Welcome to Marienplatz Guide
          </div>
          <div className="empty-state__hint">
            Ask me about sushi restaurants or parking garages near Marienplatz,
            Munich!
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list" role="log" aria-label="Chat messages">
      {messages.map((msg, index) => (
        <ChatMessageItem key={index} message={msg} />
      ))}

      {isLoading && (
        <div className="typing-indicator" aria-label="Assistant is typing">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
