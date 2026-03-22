/**
 * Typed API client for the Marienplatz POI Chatbot backend.
 *
 * All fetch logic is centralized here — components never call fetch directly.
 * Uses environment-configured API base URL. Handles errors predictably.
 */

import { API_BASE_URL } from "./config";
import { createLogger } from "./logger";
import {
  ChatError,
  type BackendErrorBody,
  type ChatRequest,
  type ChatResponse,
  type DeleteSessionResponse,
  type SessionHistoryResponse,
} from "./types";

const log = createLogger("api");

/**
 * Send a chat message to the backend.
 *
 * @param sessionId - Stable session identifier
 * @param message - User message text
 * @param lat - Optional latitude from browser geolocation
 * @param lon - Optional longitude from browser geolocation
 * @returns The assistant's chat response
 * @throws ChatError with a user-safe message
 */
export async function sendChatMessage(
  sessionId: string,
  message: string,
  lat: number | null = null,
  lon: number | null = null,
): Promise<ChatResponse> {
  const payload: ChatRequest = {
    session_id: sessionId,
    message,
    user_lat: lat,
    user_lon: lon,
  };

  log.info("Sending chat request", { sessionId, hasCoords: lat !== null });

  const response = await safeFetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorMessage = await extractErrorMessage(response);
    log.error("Chat request failed", {
      status: response.status,
      error: errorMessage,
    });
    throw new ChatError(errorMessage, response.status);
  }

  const data: ChatResponse = await response.json();
  log.info("Chat response received", {
    sessionId,
    toolCalls: data.tool_calls_made,
  });
  return data;
}

/**
 * Retrieve conversation history for a session.
 */
export async function getSessionHistory(
  sessionId: string,
): Promise<SessionHistoryResponse> {
  const response = await safeFetch(
    `${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}`,
  );

  if (!response.ok) {
    const errorMessage = await extractErrorMessage(response);
    throw new ChatError(errorMessage, response.status);
  }

  return response.json();
}

/**
 * Delete a session and its conversation history.
 */
export async function deleteSession(
  sessionId: string,
): Promise<DeleteSessionResponse> {
  const response = await safeFetch(
    `${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    const errorMessage = await extractErrorMessage(response);
    throw new ChatError(errorMessage, response.status);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Wrapper around fetch that converts network errors to ChatError.
 */
async function safeFetch(
  url: string,
  init?: RequestInit,
): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (error) {
    log.error("Network error", error);
    throw new ChatError(
      "Unable to reach the server. Please check your connection and try again.",
    );
  }
}

/**
 * Extract a user-safe error message from a non-2xx response.
 * Attempts to parse the backend's structured error body first.
 */
async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (isBackendError(body)) {
      return body.error.message;
    }
  } catch {
    // Response body is not valid JSON — fall through to default
  }

  return defaultErrorMessage(response.status);
}

/** Type guard for backend structured error response. */
function isBackendError(body: unknown): body is BackendErrorBody {
  return (
    typeof body === "object" &&
    body !== null &&
    "error" in body &&
    typeof (body as BackendErrorBody).error?.message === "string"
  );
}

/** Map common HTTP status codes to user-friendly messages. */
function defaultErrorMessage(status: number): string {
  switch (status) {
    case 400:
      return "The request was invalid. Please check your message and try again.";
    case 404:
      return "The requested resource was not found.";
    case 422:
      return "The request could not be processed. Please try rephrasing your message.";
    case 500:
      return "An internal server error occurred. Please try again later.";
    case 502:
      return "An upstream service is temporarily unavailable. Please try again in a moment.";
    default:
      return `Something went wrong (status ${status}). Please try again.`;
  }
}
