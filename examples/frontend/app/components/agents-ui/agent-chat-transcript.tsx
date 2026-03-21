import type { AgentState, ReceivedMessage } from "@livekit/components-react";

type Props = {
  agentState: AgentState;
  messages: ReceivedMessage[];
};

export function AgentChatTranscript({ agentState, messages }: Props) {
  return (
    <div className="transcript-panel">
      <div className="transcript-header">
        <h2>Transcript</h2>
        <span className="transcript-state">{humanizeAgentState(agentState)}</span>
      </div>

      <div aria-live="polite" className="transcript-list" role="log">
        {messages.length === 0 ? (
          <p className="transcript-empty">
            Start the session and speak to see user and agent transcriptions here.
          </p>
        ) : (
          messages.map((message) => (
            <article
              className={`transcript-message ${messageClassName(message)}`}
              key={message.id}
            >
              <div className="transcript-meta">
                <strong>{speakerLabel(message)}</strong>
                <span>{formatTimestamp(message.timestamp)}</span>
              </div>
              <p>{readableText(message)}</p>
            </article>
          ))
        )}
      </div>
    </div>
  );
}

function readableText(message: ReceivedMessage): string {
  return message.message;
}

function messageClassName(message: ReceivedMessage): string {
  switch (message.type) {
    case "userTranscript":
      return "transcript-user";
    case "agentTranscript":
      return "transcript-agent";
    default:
      return "transcript-chat";
  }
}

function speakerLabel(message: ReceivedMessage): string {
  switch (message.type) {
    case "userTranscript":
      return "You";
    case "agentTranscript":
      return "Agent";
    default:
      return message.from?.name ?? "Chat";
  }
}

function formatTimestamp(timestamp: number): string {
  return new Intl.DateTimeFormat([], {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

function humanizeAgentState(state: AgentState): string {
  switch (state) {
    case "pre-connect-buffering":
      return "Warming up";
    case "connecting":
      return "Connecting";
    case "initializing":
      return "Initializing";
    case "listening":
      return "Listening";
    case "thinking":
      return "Thinking";
    case "speaking":
      return "Speaking";
    case "idle":
      return "Ready";
    case "failed":
      return "Failed";
    case "disconnected":
      return "Disconnected";
  }
}
