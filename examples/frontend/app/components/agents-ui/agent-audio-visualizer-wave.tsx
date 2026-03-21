import { useMemo } from "react";
import {
  useAudioWaveform,
  type AgentState,
  type TrackReferenceOrPlaceholder,
} from "@livekit/components-react";

type VisualizerSize = "sm" | "md" | "lg";

type Props = {
  audioTrack?: TrackReferenceOrPlaceholder;
  state: AgentState;
  size?: VisualizerSize;
};

const SIZE_CONFIG: Record<
  VisualizerSize,
  { width: number; height: number; strokeWidth: number }
> = {
  sm: { width: 280, height: 68, strokeWidth: 2.5 },
  md: { width: 420, height: 96, strokeWidth: 3 },
  lg: { width: 560, height: 120, strokeWidth: 3.4 },
};

export function AgentAudioVisualizerWave({
  audioTrack,
  state,
  size = "md",
}: Props) {
  const waveform = useAudioWaveform(audioTrack, {
    barCount: 72,
    updateInterval: 28,
    volMultiplier: 2.8,
  });
  const { width, height, strokeWidth } = SIZE_CONFIG[size];

  const path = useMemo(() => {
    const centerY = height / 2;
    const samples = waveform.bars.length > 1 ? waveform.bars : new Array(72).fill(0);
    const step = width / Math.max(samples.length - 1, 1);

    return samples
      .map((value, index) => {
        const x = index * step;
        const amplitude = Math.min(value * 22, height * 0.42);
        const y = centerY - amplitude;
        return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(" ");
  }, [waveform.bars, height, width]);

  return (
    <div className={`agent-wave-shell agent-wave-${state}`}>
      <svg
        aria-label={`Agent waveform while ${state}`}
        className="agent-wave"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        <path
          className="agent-wave-baseline"
          d={`M 0 ${(height / 2).toFixed(2)} L ${width} ${(height / 2).toFixed(2)}`}
        />
        <path className="agent-wave-line" d={path} strokeWidth={strokeWidth} />
      </svg>
      <span className="agent-wave-state">{humanizeAgentState(state)}</span>
    </div>
  );
}

function humanizeAgentState(state: AgentState): string {
  switch (state) {
    case "pre-connect-buffering":
      return "Warming up audio";
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
