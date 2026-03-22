/**
 * Environment-driven frontend configuration.
 *
 * Uses Vite's import.meta.env for compile-time environment variables.
 * All VITE_-prefixed variables are exposed to the client bundle.
 */

/** Base URL for backend API requests. Empty string uses relative URLs (works with Vite proxy and static serving). */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "";

/** Timeout in ms for browser geolocation requests. */
export const GEOLOCATION_TIMEOUT_MS: number =
  Number(import.meta.env.VITE_GEOLOCATION_TIMEOUT_MS) || 3000;

/** Application title shown in the chat header. */
export const APP_TITLE: string =
  import.meta.env.VITE_APP_TITLE ?? "🍣 Marienplatz Guide";
