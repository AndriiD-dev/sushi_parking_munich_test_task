/**
 * Chat header component.
 *
 * Displays the app title and a brief subtitle.
 */

import { APP_TITLE } from "../lib/config";

export default function ChatHeader() {
  return (
    <header className="chat-header">
      <div>
        <div className="chat-header__title">{APP_TITLE}</div>
        <div className="chat-header__subtitle">
          Sushi restaurants &amp; parking near Marienplatz
        </div>
      </div>
    </header>
  );
}
