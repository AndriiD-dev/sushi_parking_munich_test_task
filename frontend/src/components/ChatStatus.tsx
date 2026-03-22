/**
 * Chat status display — error banner.
 *
 * Shows transient errors in a non-invasive banner with a dismiss button.
 */

interface ChatStatusProps {
  error: string | null;
  onDismiss: () => void;
}

export default function ChatStatus({ error, onDismiss }: ChatStatusProps) {
  if (!error) return null;

  return (
    <div className="error-banner" role="alert">
      <span>⚠️ {error}</span>
      <button
        className="error-banner__dismiss"
        onClick={onDismiss}
        aria-label="Dismiss error"
        title="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}
