# Feasibility Report: TurboQuant-GPU Integration into OpenRTC

## 1. Executive Summary

**TurboQuant-GPU cannot be integrated into OpenRTC-Python in its current form.** There is a fundamental architectural mismatch: TurboQuant-GPU operates on `past_key_values` tensors from local HuggingFace transformer forward passes, while OpenRTC has no local LLM inference path. All LLM inference is delegated to cloud API providers (OpenAI, Groq, Anthropic) through the LiveKit Agents SDK plugin system, where KV cache is managed server-side and never exposed to client code.

Enabling TurboQuant-GPU would require building an entirely new local-inference LLM plugin for the LiveKit Agents SDK — a separate engineering effort outside the scope of OpenRTC itself. Once such a plugin existed, OpenRTC integration would be minimal.

**Recommendation: No-go at this time.** Revisit if local/self-hosted LLM inference becomes a product requirement.

---

## 2. LLM Inference Path Analysis

### 2.1 How OpenRTC Handles LLM Inference Today

OpenRTC is a **multi-agent pooling layer** on top of the LiveKit Agents SDK. Its value proposition is consolidating multiple voice agents into a single worker process to share expensive resources (Silero VAD, turn detector).

The LLM inference flow:

```
AgentPool.add(llm="openai/gpt-4.1-mini")     # pool.py:307-349
         │
         ▼
AgentConfig.llm = "openai/gpt-4.1-mini"      # pool.py:141-198
         │
         ▼  (serialized via _serialize_provider_value for worker spawn)
         │
_run_universal_session()                       # pool.py:107-139
         │
         ▼
AgentSession(                                  # pool.py:116-122
    stt=config.stt,
    llm=config.llm,    ◄── passed directly to LiveKit SDK
    tts=config.tts,
    vad=ctx.proc.userdata["vad"],
)
         │
         ▼
LiveKit Agents SDK handles all inference       # OpenRTC has no further involvement
```

**Key observations:**

- OpenRTC never instantiates a transformer model, calls `model.forward()`, or accesses `past_key_values`
- The `llm=` parameter accepts either a string identifier (`"openai/gpt-4.1-mini"`) or a LiveKit plugin instance (`openai.responses.LLM(...)`) — both are cloud API clients
- Provider serialization (`_serialize_provider_value`, pool.py:573-590) handles only `livekit.plugins.*` cloud-API plugin classes
- The only shared resources loaded at prewarm time (pool.py:95-104) are Silero VAD and the multilingual turn detector — no LLM model weights

### 2.2 Where `past_key_values` Would Need to Be Intercepted

For TurboQuant-GPU to work, it needs access to the KV cache **between** generation steps of a local transformer model:

```
model.forward(input_ids)
    → output.past_key_values           ◄── TurboQuant intercepts here
    → engine.compress_kv_cache(past_kv)
    → engine.build_cache(compressed)   → standard DynamicCache
    → model.forward(..., past_key_values=cache)   ◄── passed back here
```

This interception point **does not exist** in the OpenRTC codebase because there is no local model forward pass.

### 2.3 Provider Types and Serialization

The provider system (pool.py:573-626) is designed for cloud API plugins:

- **Known fast-path providers** (pool.py:86-92): `livekit.plugins.openai.stt.STT`, `livekit.plugins.openai.tts.TTS`, `livekit.plugins.openai.responses.llm.LLM`
- **Generic path**: Any `livekit.plugins.*` class with an `_opts` attribute
- No support for local model providers, torch modules, or HuggingFace pipelines

---

## 3. Integration Architecture (If Pursued)

### 3.1 Required: A New LiveKit LLM Plugin

TurboQuant-GPU integration requires a **new LiveKit Agents SDK LLM plugin** that handles local inference:

```
AgentPool
  └── AgentSession(llm=LocalLLMPlugin(model="meta-llama/Llama-3-8B", turboquant=True))
       └── livekit-plugins-local-llm        ◄── NEW PACKAGE (does not exist)
            ├── Loads HuggingFace model onto CUDA GPU
            ├── Runs transformers generation loop
            ├── TurboQuantEngine intercepts past_key_values
            │     ├── compress_kv_cache() after each forward pass
            │     └── build_cache() returns DynamicCache for next step
            └── Streams tokens back via LiveKit LLM plugin interface
```

### 3.2 OpenRTC Changes (Minimal, Once Plugin Exists)

| File | Change | Scope |
|------|--------|-------|
| `pool.py` `_prewarm_worker` (line 95-104) | Load model weights once, store in `proc.userdata["local_llm_model"]` | ~15 lines |
| `pool.py` `_prewarm_worker` | Initialize `TurboQuantEngine` once, store in `proc.userdata["tq_engine"]` | ~5 lines |
| `pool.py` `_serialize_provider_value` (line 573-590) | Generic `livekit.plugins.*` path likely handles new plugin automatically | 0 lines (verify only) |
| `pyproject.toml` | Add optional `[local-llm]` dependency group | ~5 lines |
| `resources.py` | Add GPU memory tracking to `ProcessResidentSetInfo` | ~20 lines |

The `_prewarm_worker` extension would look conceptually like:

```python
# In _prewarm_worker (pool.py:95-104) — conceptual, NOT implementation code
if local_llm_config:
    model = AutoModelForCausalLM.from_pretrained(model_name, device_map="cuda")
    engine = TurboQuantEngine(head_dim=model.config.head_dim, total_bits=3, device="cuda")
    engine.auto_tune(seq_len=2048)
    proc.userdata["local_model"] = model
    proc.userdata["tq_engine"] = engine
```

### 3.3 Upstream Dependencies (Unknown Scope)

The **biggest unknown** is whether LiveKit Agents SDK's `LLM` base class can accommodate a local-inference plugin:

- Does the `LLM` plugin interface support streaming token generation from a local model?
- Does `AgentSession` expect the LLM plugin to manage its own conversation state?
- Can a custom plugin control the generation loop (required for KV cache interception)?

This must be validated before any implementation work begins.

---

## 4. Constraints and Tradeoffs

### 4.1 Applicability

| Agent Type | TurboQuant Benefit |
|---|---|
| Cloud API (OpenAI, Groq, Anthropic) | **None** — KV cache managed server-side |
| Local/self-hosted transformer model | **~5x KV cache compression** |

OpenRTC currently supports **only** cloud API agents. TurboQuant-GPU only becomes relevant if local model support is added.

### 4.2 Quality Impact

- 3-bit compression: cosine similarity >= 0.98 with original cache
- For voice agent conversations (short turns, conversational language), this quality level is likely acceptable
- TurboQuant's `auto_tune()` can benchmark 2-bit vs 3-bit to find the optimal tradeoff per model

### 4.3 Latency Impact

- TurboQuant adds ~1-5ms per turn for KV cache compression/decompression on GPU
- OpenRTC voice pipeline latency budget: typically 200-500ms per turn (STT → LLM → TTS)
- **1-5ms overhead is negligible** (<1% of total turn latency)
- However, local model inference itself is slower than cloud API calls for smaller models — the bottleneck is the generation speed, not KV cache compression

### 4.4 Memory Impact (Projected)

For a 7B model at 4K context with OpenRTC's shared-worker architecture:

| Metric | Without TurboQuant | With TurboQuant |
|---|---|---|
| Model weights (shared) | ~14 GB (FP16) | ~14 GB (FP16) |
| KV cache per session | ~1.6 GB | ~320 MB |
| 5 concurrent sessions | 14 + 8 = 22 GB | 14 + 1.6 = 15.6 GB |
| 10 concurrent sessions | 14 + 16 = 30 GB | 14 + 3.2 = 17.2 GB |
| Max sessions on 24GB GPU | ~6 | ~31 |

The benefit compounds with OpenRTC's pooling model: weights loaded once + compressed per-session cache = dramatically more concurrent sessions per GPU.

---

## 5. Risks and Open Questions

1. **LiveKit SDK plugin interface compatibility** — Can a local-inference plugin with custom generation loop conform to the LiveKit `LLM` interface? This is the single biggest risk and must be investigated first.

2. **Model loading and sharing** — OpenRTC's `_prewarm_worker` runs once per worker process. Sharing a single model across concurrent sessions requires careful handling of concurrent forward passes (or request batching).

3. **CUDA dependency** — Adding `torch` and CUDA to OpenRTC's dependency tree significantly increases the install footprint. This should be strictly optional.

4. **Operational complexity** — Users deploying local models need GPU infrastructure, model storage, and CUDA drivers — a different operational model than cloud API agents.

5. **TurboQuant determinism** — Rotation matrices (Pi, S) are seeded and deterministic, so a single `TurboQuantEngine` instance can be shared across sessions. But concurrent access to the engine's internal state needs thread-safety verification.

---

## 6. Recommendation

### Verdict: No-Go (At This Time)

The prerequisites for TurboQuant-GPU integration — specifically, a local-inference LLM plugin for LiveKit Agents SDK — represent a substantial engineering effort that is orthogonal to OpenRTC's current mission of multi-agent pooling for cloud-API-backed voice agents.

### If Local LLM Becomes a Priority

| Phase | Description | Estimated Effort |
|---|---|---|
| **Phase 0** | Audit LiveKit SDK's `LLM` plugin interface for local-inference feasibility | 1-2 weeks |
| **Phase 1** | Build standalone `livekit-plugins-local-llm` package | 4-6 weeks |
| **Phase 2** | Integrate TurboQuantEngine into the plugin's generation loop | 2-3 weeks |
| **Phase 3** | OpenRTC integration: prewarm model loading + provider registration | 1-2 weeks |

**Phase 0 is the critical gate** — it determines whether the entire approach is viable before any implementation work begins.

### Alternative Approaches

If the goal is to reduce LLM costs rather than specifically use local models:

- **Prompt optimization**: Reduce token usage in voice agent conversations
- **Model selection**: Use smaller/cheaper cloud models where quality permits
- **Caching**: Cache common LLM responses for repeated queries (e.g., greetings, FAQ)
- **Hybrid routing**: Route simple queries to smaller models, complex ones to larger models

These approaches work within OpenRTC's existing cloud-API architecture and require no infrastructure changes.
