/**
 * Tests for the API client module.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { sendChatMessage, getSessionHistory, deleteSession } from "../lib/api";
import { ChatError } from "../lib/types";

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("sendChatMessage", () => {
  it("sends correct payload with session ID and coordinates", async () => {
    const mockResponse = {
      session_id: "test-session",
      reply: "Hello!",
      tool_calls_made: [],
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await sendChatMessage("test-session", "Hi", 48.137, 11.575);

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/chat");
    expect(options.method).toBe("POST");

    const body = JSON.parse(options.body);
    expect(body.session_id).toBe("test-session");
    expect(body.message).toBe("Hi");
    expect(body.user_lat).toBe(48.137);
    expect(body.user_lon).toBe(11.575);

    expect(result).toEqual(mockResponse);
  });

  it("sends null coordinates when geolocation is unavailable", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          session_id: "s1",
          reply: "Reply",
          tool_calls_made: [],
        }),
    });

    await sendChatMessage("s1", "Hello");

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.user_lat).toBeNull();
    expect(body.user_lon).toBeNull();
  });

  it("throws ChatError with backend error message on 400", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: () =>
        Promise.resolve({
          error: { code: "INVALID_REQUEST", message: "Message is required" },
        }),
    });

    await expect(sendChatMessage("s1", "")).rejects.toThrow(ChatError);
    await expect(
      sendChatMessage("s1", "retry"),
    ).rejects.toThrow();
  });

  it("throws ChatError with default message on non-JSON error response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("not JSON")),
    });

    try {
      await sendChatMessage("s1", "test");
      expect.unreachable("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ChatError);
      expect((err as ChatError).userMessage).toContain("internal server error");
    }
  });

  it("throws ChatError on network failure", async () => {
    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    try {
      await sendChatMessage("s1", "test");
      expect.unreachable("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ChatError);
      expect((err as ChatError).userMessage).toContain("Unable to reach");
    }
  });
});

describe("getSessionHistory", () => {
  it("fetches session history", async () => {
    const mockHistory = {
      session_id: "s1",
      messages: [{ role: "user", content: "Hi" }],
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockHistory),
    });

    const result = await getSessionHistory("s1");
    expect(result).toEqual(mockHistory);
    expect(mockFetch.mock.calls[0][0]).toContain("/sessions/s1");
  });
});

describe("deleteSession", () => {
  it("deletes a session", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ session_id: "s1", deleted: true }),
    });

    const result = await deleteSession("s1");
    expect(result.deleted).toBe(true);
  });
});
