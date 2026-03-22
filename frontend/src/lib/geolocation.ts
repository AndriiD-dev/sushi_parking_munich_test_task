/**
 * Browser geolocation helper.
 *
 * Wraps navigator.geolocation in a Promise with configurable timeout.
 * Returns coordinates or null — never throws, never blocks forever.
 */

import { GEOLOCATION_TIMEOUT_MS } from "./config";
import { createLogger } from "./logger";
import type { Coordinates } from "./types";

const log = createLogger("geolocation");

/**
 * Attempt to get the user's current coordinates from the browser.
 *
 * @returns Coordinates if available, null otherwise.
 */
export function getCurrentCoordinates(): Promise<Coordinates | null> {
  if (!navigator.geolocation) {
    log.info("Geolocation API not available");
    return Promise.resolve(null);
  }

  return new Promise<Coordinates | null>((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;

        // Validate coordinates are finite numbers in valid range
        if (!isValidCoordinate(latitude, longitude)) {
          log.warn("Invalid coordinates received", { latitude, longitude });
          resolve(null);
          return;
        }

        log.info("Geolocation acquired", {
          lat: latitude.toFixed(4),
          lon: longitude.toFixed(4),
        });
        resolve({ lat: latitude, lon: longitude });
      },
      (error) => {
        const reason = geolocationErrorReason(error);
        log.info(`Geolocation unavailable: ${reason}`);
        resolve(null);
      },
      {
        enableHighAccuracy: false,
        timeout: GEOLOCATION_TIMEOUT_MS,
        maximumAge: 60_000, // Accept cached position up to 1 minute old
      },
    );
  });
}

/** Validate that both coordinates are finite and within valid geographic range. */
function isValidCoordinate(lat: number, lon: number): boolean {
  return (
    Number.isFinite(lat) &&
    Number.isFinite(lon) &&
    lat >= -90 &&
    lat <= 90 &&
    lon >= -180 &&
    lon <= 180
  );
}

/** Map GeolocationPositionError codes to human-readable reasons. */
function geolocationErrorReason(error: GeolocationPositionError): string {
  switch (error.code) {
    case error.PERMISSION_DENIED:
      return "permission denied";
    case error.POSITION_UNAVAILABLE:
      return "position unavailable";
    case error.TIMEOUT:
      return "timeout";
    default:
      return "unknown error";
  }
}
