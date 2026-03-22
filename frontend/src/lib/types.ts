/**
 * Shared frontend types aligned with the backend API contract.
 */

/** A single chat message displayed in the UI. */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

/** Request payload for POST /chat. */
export interface ChatRequest {
  session_id: string;
  message: string;
  user_lat: number | null;
  user_lon: number | null;
}

/** Successful response from POST /chat. */
export interface ChatResponse {
  session_id: string;
  reply: string;
  tool_calls_made: string[];
}

/** Session history response from GET /sessions/{id}. */
export interface SessionHistoryResponse {
  session_id: string;
  messages: Array<{ role: string; content?: string }>;
}

/** Session deletion response from DELETE /sessions/{id}. */
export interface DeleteSessionResponse {
  session_id: string;
  deleted: boolean;
}

/** Structured error body returned by the backend. */
export interface BackendErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

/** Browser geolocation coordinates. */
export interface Coordinates {
  lat: number;
  lon: number;
}

/** Frontend-specific error with a user-safe message. */
export class ChatError extends Error {
  constructor(
    public readonly userMessage: string,
    public readonly statusCode?: number,
    public readonly code?: string,
  ) {
    super(userMessage);
    this.name = "ChatError";
  }
}
