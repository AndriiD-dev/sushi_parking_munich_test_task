/**
 * Custom hook managing chat session state and message submission.
 *
 * Encapsulates session ID lifecycle, message history, loading/error state,
 * geolocation integration, and API calls. Components only need the
 * returned state and sendMessage function.
 */

import { useCallback, useRef, useState } from "react";
import { sendChatMessage } from "../lib/api";
import { getCurrentCoordinates } from "../lib/geolocation";
import { createLogger } from "../lib/logger";
import type { ChatMessage } from "../lib/types";
import { ChatError } from "../lib/types";

const log = createLogger("useChatSession");

const SESSION_STORAGE_KEY = "marienplatz_session_id";

/** Get or create a stable session ID for the current browser session. */
function getSessionId(): string {
  const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const id = crypto.randomUUID();
  sessionStorage.setItem(SESSION_STORAGE_KEY, id);
  log.info("New session created", { sessionId: id });
  return id;
}

export interface UseChatSessionReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sessionId: string;
  sendMessage: (text: string) => Promise<void>;
  clearError: () => void;
}

export function useChatSession(): UseChatSessionReturn {
  const sessionIdRef = useRef(getSessionId());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    // Optimistic UI: append user message immediately
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setIsLoading(true);
    setError(null);

    try {
      // Attempt geolocation (non-blocking, returns null on failure)
      const coords = await getCurrentCoordinates();

      const response = await sendChatMessage(
        sessionIdRef.current,
        trimmed,
        coords?.lat ?? null,
        coords?.lon ?? null,
      );

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.reply || "I received your message but have nothing to add.",
        },
      ]);
    } catch (err) {
      const userMessage =
        err instanceof ChatError
          ? err.userMessage
          : "Something went wrong. Please try again.";

      log.error("Message send failed", err);
      setError(userMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    messages,
    isLoading,
    error,
    sessionId: sessionIdRef.current,
    sendMessage,
    clearError,
  };
}
