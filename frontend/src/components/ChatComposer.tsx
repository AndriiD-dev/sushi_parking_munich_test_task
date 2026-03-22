/**
 * Chat input composer with text field and send button.
 *
 * Handles form submission, disabled state during loading,
 * and keyboard shortcuts (Enter to send).
 */

import { useState } from "react";

interface ChatComposerProps {
  onSubmit: (message: string) => void;
  isLoading: boolean;
}

export default function ChatComposer({
  onSubmit,
  isLoading,
}: ChatComposerProps) {
  const [input, setInput] = useState("");

  const canSend = input.trim().length > 0 && !isLoading;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSend) return;
    onSubmit(input.trim());
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSend) {
        onSubmit(input.trim());
        setInput("");
      }
    }
  }

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <input
        id="chat-input"
        className="composer__input"
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message…"
        disabled={isLoading}
        aria-label="Chat message input"
        autoComplete="off"
      />
      <button
        id="chat-send-button"
        className="composer__button"
        type="submit"
        disabled={!canSend}
        aria-label="Send message"
        title="Send message"
      >
        ↑
      </button>
    </form>
  );
}
