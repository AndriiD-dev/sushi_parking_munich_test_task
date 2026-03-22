/**
 * Tests for the useChatSession hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useChatSession } from "../hooks/useChatSession";

// Mock the API module
vi.mock("../lib/api", () => ({
  sendChatMessage: vi.fn(),
}));

// Mock the geolocation module
vi.mock("../lib/geolocation", () => ({
  getCurrentCoordinates: vi.fn(),
}));

// Import mocked modules
import { sendChatMessage } from "../lib/api";
import { getCurrentCoordinates } from "../lib/geolocation";
import { ChatError } from "../lib/types";

const mockSendChatMessage = vi.mocked(sendChatMessage);
const mockGetCoordinates = vi.mocked(getCurrentCoordinates);

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((_index: number) => null),
  };
})();

beforeEach(() => {
  vi.stubGlobal("sessionStorage", sessionStorageMock);
  vi.stubGlobal("crypto", {
    randomUUID: () => "test-uuid-1234",
  });
  sessionStorageMock.clear();
  mockSendChatMessage.mockReset();
  mockGetCoordinates.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useChatSession", () => {
  it("initializes with empty messages and no error", () => {
    const { result } = renderHook(() => useChatSession());

    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.sessionId).toBe("test-uuid-1234");
  });

  it("sends message and appends assistant reply", async () => {
    mockGetCoordinates.mockResolvedValue({ lat: 48.137, lon: 11.575 });
    mockSendChatMessage.mockResolvedValue({
      session_id: "test-uuid-1234",
      reply: "Here are some sushi restaurants!",
      tool_calls_made: ["search_sushi_restaurants"],
    });

    const { result } = renderHook(() => useChatSession());

    await act(async () => {
      await result.current.sendMessage("Find sushi near me");
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toEqual({
      role: "user",
      content: "Find sushi near me",
    });
    expect(result.current.messages[1]).toEqual({
      role: "assistant",
      content: "Here are some sushi restaurants!",
    });
    expect(result.current.isLoading).toBe(false);

    // Verify coordinates were passed
    expect(mockSendChatMessage).toHaveBeenCalledWith(
      "test-uuid-1234",
      "Find sushi near me",
      48.137,
      11.575,
    );
  });

  it("sends message without coordinates when geolocation fails", async () => {
    mockGetCoordinates.mockResolvedValue(null);
    mockSendChatMessage.mockResolvedValue({
      session_id: "test-uuid-1234",
      reply: "Reply without location",
      tool_calls_made: [],
    });

    const { result } = renderHook(() => useChatSession());

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    expect(mockSendChatMessage).toHaveBeenCalledWith(
      "test-uuid-1234",
      "Hello",
      null,
      null,
    );
    expect(result.current.messages).toHaveLength(2);
  });

  it("shows error and preserves history on backend failure", async () => {
    mockGetCoordinates.mockResolvedValue(null);
    mockSendChatMessage
      .mockResolvedValueOnce({
        session_id: "test-uuid-1234",
        reply: "First reply",
        tool_calls_made: [],
      })
      .mockRejectedValueOnce(
        new ChatError("Server is unavailable", 502),
      );

    const { result } = renderHook(() => useChatSession());

    // First message succeeds
    await act(async () => {
      await result.current.sendMessage("First");
    });

    expect(result.current.messages).toHaveLength(2);

    // Second message fails
    await act(async () => {
      await result.current.sendMessage("Second");
    });

    // Prior messages are kept, user message added, error shown
    expect(result.current.messages).toHaveLength(3);
    expect(result.current.messages[2]).toEqual({
      role: "user",
      content: "Second",
    });
    expect(result.current.error).toBe("Server is unavailable");
    expect(result.current.isLoading).toBe(false);
  });

  it("clears error with clearError", async () => {
    mockGetCoordinates.mockResolvedValue(null);
    mockSendChatMessage.mockRejectedValue(
      new ChatError("Error occurred"),
    );

    const { result } = renderHook(() => useChatSession());

    await act(async () => {
      await result.current.sendMessage("Test");
    });

    expect(result.current.error).toBe("Error occurred");

    act(() => {
      result.current.clearError();
    });

    await waitFor(() => {
      expect(result.current.error).toBeNull();
    });
  });

  it("ignores empty/whitespace messages", async () => {
    const { result } = renderHook(() => useChatSession());

    await act(async () => {
      await result.current.sendMessage("   ");
    });

    expect(result.current.messages).toHaveLength(0);
    expect(mockSendChatMessage).not.toHaveBeenCalled();
  });
});
