import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import {
  RoomAudioRenderer,
  SessionEvent,
  StartAudio,
  useAgent,
  useSession,
  useSessionContext,
  useSessionMessages,
} from "@livekit/components-react";
import { RoomEvent, TokenSource, type ConnectionState } from "livekit-client";

import { AgentAudioVisualizerWave } from "~/components/agents-ui/agent-audio-visualizer-wave";
import { AgentChatTranscript } from "~/components/agents-ui/agent-chat-transcript";
import { AgentSessionProvider } from "~/components/agents-ui/agent-session-provider";
import type { DemoDefinition } from "~/lib/demo-config";

type CallPhase = "idle" | "requesting-token" | "connecting" | "connected";

type Props = {
  demo: DemoDefinition;
};

export function DemoCallPage({ demo }: Props) {
  const tokenSource = useMemo(() => TokenSource.endpoint("/api/token"), []);
  const session = useSession(tokenSource, { agentName: demo.agent });
  const room = session.room;
  const sessionEmitter = session.internal.emitter;
  const [phase, setPhase] = useState<CallPhase>("idle");
  const [roomMetadata, setRoomMetadata] = useState<string>("");
  const [remoteParticipantCount, setRemoteParticipantCount] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    const syncRuntime = () => {
      setRoomMetadata(room.metadata ?? "");
      setRemoteParticipantCount(room.remoteParticipants.size);
    };

    const handleConnected = () => {
      syncRuntime();
      setPhase("connected");
    };
    const handleRoomMetadataChanged = (nextMetadata: string | undefined) => {
      setRoomMetadata(nextMetadata ?? "");
    };
    const handleDisconnected = () => {
      setRemoteParticipantCount(0);
      setRoomMetadata("");
      setPhase("idle");
    };
    const handleConnectionStateChanged = (state: ConnectionState) => {
      if (state === "connecting") {
        setPhase("connecting");
      }
      if (state === "connected") {
        setPhase("connected");
      }
      if (state === "disconnected") {
        setPhase("idle");
      }
    };
    const handleMediaError = (error: Error) => {
      setErrorMessage(error.message);
    };

    syncRuntime();
    room.on(RoomEvent.Connected, handleConnected);
    room.on(RoomEvent.ParticipantConnected, syncRuntime);
    room.on(RoomEvent.ParticipantDisconnected, syncRuntime);
    room.on(RoomEvent.RoomMetadataChanged, handleRoomMetadataChanged);
    room.on(RoomEvent.Disconnected, handleDisconnected);
    sessionEmitter.on(SessionEvent.ConnectionStateChanged, handleConnectionStateChanged);
    sessionEmitter.on(SessionEvent.MediaDevicesError, handleMediaError);

    return () => {
      room.off(RoomEvent.Connected, handleConnected);
      room.off(RoomEvent.ParticipantConnected, syncRuntime);
      room.off(RoomEvent.ParticipantDisconnected, syncRuntime);
      room.off(RoomEvent.RoomMetadataChanged, handleRoomMetadataChanged);
      room.off(RoomEvent.Disconnected, handleDisconnected);
      sessionEmitter.off(SessionEvent.ConnectionStateChanged, handleConnectionStateChanged);
      sessionEmitter.off(SessionEvent.MediaDevicesError, handleMediaError);
    };
  }, [room, sessionEmitter]);

  useEffect(() => {
    return () => {
      void room.disconnect();
    };
  }, [room]);

  async function startCall() {
    setErrorMessage("");
    setPhase("requesting-token");

    try {
      await session.start({
        roomConnectOptions: {
          autoSubscribe: true,
        },
      });
      setRoomMetadata(room.metadata ?? "");
      setRemoteParticipantCount(room.remoteParticipants.size);
      setPhase("connected");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Could not start the LiveKit call.",
      );
      await disconnectFromRoom();
    }
  }

  async function disconnectFromRoom() {
    await room.disconnect();
    setPhase("idle");
    setRemoteParticipantCount(0);
    setRoomMetadata("");
  }

  return (
    <main className={`demo-shell ${demo.accentClassName}`}>
      <AgentSessionProvider session={session}>
        <RoomAudioRenderer />
        <section className="demo-panel">
          <div className="demo-topbar">
            <Link className="back-link" to="/">
              Back
            </Link>
            <span className="agent-chip">{demo.title}</span>
          </div>

          <div className="demo-hero">
            <p className="eyebrow">Single worker, targeted dispatch</p>
            <h1>{demo.title}</h1>
            <p className="hero-copy">{demo.tagline}</p>
            <p className="support-copy">{demo.description}</p>
          </div>

          <div className="status-grid">
            <StatusCard label="Frontend mode" value={demo.slug} />
            <StatusCard label="Backend agent" value={demo.agent} />
            <StatusCard label="Room" value={room.name || "Not created yet"} />
            <StatusCard
              label="Connection"
              value={humanizeConnectionState(phase, session.connectionState)}
            />
          </div>

          <div className="call-actions">
            <button
              className="primary-button"
              disabled={
                phase === "requesting-token" ||
                phase === "connecting" ||
                session.isConnected
              }
              onClick={() => {
                void startCall();
              }}
              type="button"
            >
              {phase === "requesting-token"
                ? "Creating room..."
                : phase === "connecting"
                  ? "Connecting..."
                  : demo.buttonLabel}
            </button>

            <button
              className="secondary-button"
              disabled={!session.isConnected && phase === "idle"}
              onClick={() => {
                void disconnectFromRoom();
              }}
              type="button"
            >
              Disconnect
            </button>

            <StartAudio className="secondary-button" label="Enable speaker audio" />
          </div>

          <LiveCallPanel />

          <div className="notes-panel">
            <h2>What this demo proves</h2>
            <ul>
              <li>This page always requests the <code>{demo.agent}</code> agent.</li>
              <li>The token route creates a room with matching room metadata.</li>
              <li>The Python worker reads that metadata and dispatches the correct agent.</li>
              <li>Remote audio now plays in the browser and transcripts update live.</li>
            </ul>
          </div>

          <div className="runtime-panel">
            <div>
              <span className="runtime-label">Remote participants</span>
              <strong>{remoteParticipantCount}</strong>
            </div>
            <div>
              <span className="runtime-label">Room metadata</span>
              <code>{roomMetadata || '{"agent": "..."}'}</code>
            </div>
          </div>

          {errorMessage ? <p className="error-banner">{errorMessage}</p> : null}
        </section>
      </AgentSessionProvider>
    </main>
  );
}

function LiveCallPanel() {
  const { microphoneTrack, state } = useAgent();
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);

  return (
    <section className="live-call-grid">
      <div className="live-call-card visualizer-card">
        <div className="live-call-heading">
          <h2>Agent audio</h2>
          <span>Voice activity and speaking state</span>
        </div>
        <AgentAudioVisualizerWave audioTrack={microphoneTrack} size="lg" state={state} />
      </div>

      <AgentChatTranscript agentState={state} messages={messages} />
    </section>
  );
}

function StatusCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function humanizeConnectionState(
  phase: CallPhase,
  state: ConnectionState,
): string {
  if (phase === "requesting-token") {
    return "Requesting token";
  }
  if (phase === "connecting") {
    return "Connecting";
  }
  if (phase === "connected") {
    return "Connected";
  }
  if (state === "reconnecting" || state === "signalReconnecting") {
    return "Reconnecting";
  }
  return "Idle";
}
