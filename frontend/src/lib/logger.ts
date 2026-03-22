/**
 * Lightweight frontend logger.
 *
 * Logs key flows (request lifecycle, geolocation, errors) at a useful level.
 * Easy to disable or upgrade to a structured logging library later.
 */

type LogLevel = "debug" | "info" | "warn" | "error";

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const MIN_LEVEL: number =
  LOG_LEVELS[(import.meta.env.VITE_LOG_LEVEL as LogLevel) ?? "info"] ??
  LOG_LEVELS.info;

function shouldLog(level: LogLevel): boolean {
  return LOG_LEVELS[level] >= MIN_LEVEL;
}

function formatPrefix(level: LogLevel, context: string): string {
  return `[${level.toUpperCase()}] [${context}]`;
}

/**
 * Create a scoped logger for a specific module.
 *
 * @example
 * const log = createLogger("api");
 * log.info("Request sent", { sessionId });
 */
export function createLogger(context: string) {
  return {
    debug(message: string, data?: unknown) {
      if (shouldLog("debug")) {
        console.debug(formatPrefix("debug", context), message, data ?? "");
      }
    },
    info(message: string, data?: unknown) {
      if (shouldLog("info")) {
        console.info(formatPrefix("info", context), message, data ?? "");
      }
    },
    warn(message: string, data?: unknown) {
      if (shouldLog("warn")) {
        console.warn(formatPrefix("warn", context), message, data ?? "");
      }
    },
    error(message: string, data?: unknown) {
      if (shouldLog("error")) {
        console.error(formatPrefix("error", context), message, data ?? "");
      }
    },
  };
}
