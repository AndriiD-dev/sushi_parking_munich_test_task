/**
 * Tests for the geolocation helper.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { getCurrentCoordinates } from "../lib/geolocation";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("getCurrentCoordinates", () => {
  it("returns coordinates when geolocation succeeds", async () => {
    const mockPosition = {
      coords: { latitude: 48.1374, longitude: 11.5755 },
    };

    vi.stubGlobal("navigator", {
      geolocation: {
        getCurrentPosition: (
          success: PositionCallback,
        ) => {
          success(mockPosition as GeolocationPosition);
        },
      },
    });

    const result = await getCurrentCoordinates();
    expect(result).toEqual({ lat: 48.1374, lon: 11.5755 });
  });

  it("returns null when permission is denied", async () => {
    vi.stubGlobal("navigator", {
      geolocation: {
        getCurrentPosition: (
          _success: PositionCallback,
          error: PositionErrorCallback,
        ) => {
          error({
            code: 1,
            message: "User denied",
            PERMISSION_DENIED: 1,
            POSITION_UNAVAILABLE: 2,
            TIMEOUT: 3,
          } as GeolocationPositionError);
        },
      },
    });

    const result = await getCurrentCoordinates();
    expect(result).toBeNull();
  });

  it("returns null when geolocation times out", async () => {
    vi.stubGlobal("navigator", {
      geolocation: {
        getCurrentPosition: (
          _success: PositionCallback,
          error: PositionErrorCallback,
        ) => {
          error({
            code: 3,
            message: "Timeout",
            PERMISSION_DENIED: 1,
            POSITION_UNAVAILABLE: 2,
            TIMEOUT: 3,
          } as GeolocationPositionError);
        },
      },
    });

    const result = await getCurrentCoordinates();
    expect(result).toBeNull();
  });

  it("returns null when geolocation API is not available", async () => {
    vi.stubGlobal("navigator", { geolocation: undefined });

    const result = await getCurrentCoordinates();
    expect(result).toBeNull();
  });

  it("returns null for invalid coordinate values", async () => {
    vi.stubGlobal("navigator", {
      geolocation: {
        getCurrentPosition: (success: PositionCallback) => {
          success({
            coords: { latitude: NaN, longitude: 11.5755 },
          } as GeolocationPosition);
        },
      },
    });

    const result = await getCurrentCoordinates();
    expect(result).toBeNull();
  });
});
