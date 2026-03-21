# Provider reference

Read this when configuring non-default providers, using provider objects instead
of strings, or looking up which environment variable a provider needs.

## String format

`provider/model` or `provider/model:variant`. Passed through to `livekit-agents`.

### STT

| String | Provider |
|---|---|
| `deepgram/nova-3` | Deepgram Nova 3 |
| `deepgram/nova-3:multi` | Deepgram Nova 3 multilingual |
| `assemblyai/...` | AssemblyAI |
| `google/...` | Google Cloud STT |

### LLM

| String | Provider |
|---|---|
| `openai/gpt-4.1-mini` | OpenAI GPT-4.1 Mini |
| `openai/gpt-4.1` | OpenAI GPT-4.1 |
| `groq/llama-4-scout` | Groq Llama 4 Scout |
| `anthropic/claude-sonnet-4-20250514` | Anthropic Claude Sonnet 4 |

### TTS

| String | Provider |
|---|---|
| `cartesia/sonic-3` | Cartesia Sonic 3 |
| `elevenlabs/...` | ElevenLabs |
| `openai/tts-1` | OpenAI TTS-1 |

## Provider objects

Use when you need custom parameters or non-default endpoints:

```python
from livekit.plugins import openai

pool = AgentPool(
    default_stt=openai.STT(model="gpt-4o-mini-transcribe"),
    default_llm=openai.responses.LLM(model="gpt-4.1-mini"),
    default_tts=openai.TTS(model="gpt-4o-mini-tts"),
)
```

OpenRTC has built-in pickle support for `livekit.plugins.openai` STT, TTS, and
LLM types. Other provider objects must be natively pickleable or use string
identifiers instead.

## Environment variables

| Provider | Variable |
|---|---|
| LiveKit | `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` |
| Deepgram | `DEEPGRAM_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Cartesia | `CARTESIA_API_KEY` |
| Groq | `GROQ_API_KEY` |
| ElevenLabs | `ELEVENLABS_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| AssemblyAI | `ASSEMBLYAI_API_KEY` |
