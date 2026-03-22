/**
 * App root component.
 *
 * Composes the chat layout from focused child components.
 * Delegates state and API logic to the useChatSession hook.
 */

import ChatComposer from "./components/ChatComposer";
import ChatHeader from "./components/ChatHeader";
import ChatMessageList from "./components/ChatMessageList";
import ChatStatus from "./components/ChatStatus";
import { useChatSession } from "./hooks/useChatSession";

export default function App() {
  const { messages, isLoading, error, sendMessage, clearError } =
    useChatSession();

  return (
    <div className="app-container">
      <ChatHeader />
      <ChatMessageList messages={messages} isLoading={isLoading} />
      <ChatStatus error={error} onDismiss={clearError} />
      <ChatComposer onSubmit={sendMessage} isLoading={isLoading} />
    </div>
  );
}
