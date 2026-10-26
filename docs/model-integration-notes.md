# Model Integration Notes (story A3): EmberScan

Event: Meta Global AI Developer Hackathon, kickoff day 2026-10-26.
Method: read-only review of official pages only (Meta dev docs, Cerebral Valley event page, Baseten / Modal / Fireworks docs, and the official npm/PyPI registry entries for Meta's SAM parsers). Nothing was signed up for, no keys were created, no credits were claimed, no forms were submitted, and no API calls were made.
Every fact below was checked against the official docs on 2026-10-26. Items flagged **CHANGED** or **NEW** differ from what Meta had published before the event.

Legend: **VERIFY** means I could not confirm it on an official page today. "Inference" means my own reasoning from the docs, not a documented fact.

## Source register

Every fact cites a source ID. **All sources were accessed 2026-10-26.**

| ID | URL | Accessed |
|---|---|---|
| CV1 | https://cerebralvalley.ai/e/meta-ai-developer-hackathon | 2026-10-26 |
| CV2 | https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details (participant guide) | 2026-10-26: **redirects to the CV login page**, so it could not be read without signing in |
| M-idx | https://dev.meta.ai/docs/ | 2026-10-26 |
| M-ov | https://dev.meta.ai/docs/overview | 2026-10-26 |
| M-qs | https://dev.meta.ai/docs/quickstart | 2026-10-26 |
| M-auth | https://dev.meta.ai/docs/authentication | 2026-10-26 |
| M-mod | https://dev.meta.ai/docs/models.md | 2026-10-26 |
| M-price | https://dev.meta.ai/docs/pricing-rate-limits | 2026-10-26 |
| M-tool | https://dev.meta.ai/docs/tool-calling | 2026-10-26 |
| M-so | https://dev.meta.ai/docs/structured-output | 2026-10-26 |
| M-tok | https://dev.meta.ai/docs/token-counting | 2026-10-26 |
| M-reas | https://dev.meta.ai/docs/reasoning | 2026-10-26 |
| M-vid | https://dev.meta.ai/docs/video-understanding | 2026-10-26 |
| M-img | https://dev.meta.ai/docs/image-understanding | 2026-10-26 |
| M-file | https://dev.meta.ai/docs/file-handling | 2026-10-26 |
| M-cbf | https://dev.meta.ai/docs/cookbook/api-fundamentals | 2026-10-26 |
| M-sam-ov | https://dev.meta.ai/docs/sam/overview | 2026-10-26 |
| M-sam-seg | https://dev.meta.ai/docs/sam/segmenting | 2026-10-26 |
| M-sam-read | https://dev.meta.ai/docs/sam/reading-segmentation | 2026-10-26 |
| M-sam-lib | https://dev.meta.ai/docs/sam/client-libraries | 2026-10-26 |
| M-sam-cb | https://dev.meta.ai/docs/cookbook/sam | 2026-10-26 |
| NPM-sam | https://registry.npmjs.org/@meta-sam/parser/latest | 2026-10-26 |
| PYPI-sam | https://pypi.org/pypi/meta-sam-parser/json | 2026-10-26 |
| M-stt | https://dev.meta.ai/docs/speech-to-text | 2026-10-26 |
| M-stt-api | https://dev.meta.ai/docs/api-reference/voice/transcribe | 2026-10-26 |
| M-imgen | https://dev.meta.ai/docs/image-generation | 2026-10-26 |
| M-imgcb | https://dev.meta.ai/docs/cookbook/muse-image | 2026-10-26 |
| M-ow | https://dev.meta.ai/docs/open-weight-models | 2026-10-26 |
| M-mso | https://dev.meta.ai/docs/muse-spark-open | 2026-10-26 |
| M-mso-dep | https://dev.meta.ai/docs/muse-spark-open/deploy | 2026-10-26 |
| M-mg | https://dev.meta.ai/docs/muse-glimmer | 2026-10-26 |
| M-mg-get | https://dev.meta.ai/docs/muse-glimmer/get-the-model | 2026-10-26 |
| M-mg-dep | https://dev.meta.ai/docs/muse-glimmer/deploy | 2026-10-26 |
| HF-mso | https://huggingface.co/meta-models/Muse-Spark-Open-816B-A42B (license: `/blob/main/LICENSE.md`) | 2026-10-26 |
| HF-mg | https://huggingface.co/meta-models/Muse-Glimmer-30B | 2026-10-26 |
| M-mc | https://dev.meta.ai/docs/muse-code | 2026-10-26 |
| M-mc-auth | https://dev.meta.ai/docs/muse-code/auth | 2026-10-26 |
| M-mc-sub | https://dev.meta.ai/docs/muse-code/subscriptions | 2026-10-26 |
| BT-lib | https://www.baseten.co/library/muse-spark-open | 2026-10-26 |
| BT-price | https://www.baseten.co/pricing/ | 2026-10-26 |
| BT-api | https://docs.baseten.co/development/model-apis/overview | 2026-10-26 |
| BT-rl | https://docs.baseten.co/development/model-apis/rate-limits-and-budgets | 2026-10-26 |
| BT-so | https://docs.baseten.co/inference/structured-outputs | 2026-10-26 |
| MD-lib | https://modal.com/library/meta/muse-spark-open | 2026-10-26 |
| MD-mg | https://modal.com/library/meta/muse-glimmer-30b-bf16 (an NVFP4 page also exists: `/library/meta/muse-glimmer-30b-nvfp4`) | 2026-10-26 |
| MD-ep | https://modal.com/docs/guide/endpoints | 2026-10-26 |
| FW-mso | https://fireworks.ai/models/fireworks/muse-spark-open | 2026-10-26 |
| FW-mg | https://fireworks.ai/models/fireworks/muse-glimmer-30b | 2026-10-26 |
| FW-fc | https://docs.fireworks.ai/guides/function-calling | 2026-10-26 |

> **Participant guide (CV2):** today it redirects to `cerebralvalley.ai/auth/login`. I did not sign in. Its sub-pages (Overview, Quickstart, Model list, API cookbook, API fundamentals, OSS model cookbook) appear to map to Meta pages I read directly (M-ov, M-qs, M-mod, M-idx cookbook, M-cbf, M-ow / `/docs/cookbook/run-locally`). That mapping is **VERIFY**: Jude should sign in and confirm the links, plus anything guide-only (prize list, credits, rules).

---

## 1. Meta Model API basics

| Field | Value | Source |
|---|---|---|
| Base URL | `https://api.meta.ai/v1` | M-mod, M-qs |
| Auth header | `Authorization: Bearer $MODEL_API_KEY`. Keys start with `LLM_` and are shown once (Dashboard > API keys > Create API key). Keys on a team share rate limits. | M-auth |
| Env var | `MODEL_API_KEY`. The OpenAI SDK does **not** read it automatically, so pass `api_key=` explicitly. | M-auth, M-qs |
| SDK | OpenAI SDK (`pip install openai` / `npm install openai`) with `base_url` set to the base URL. Requests and curl examples are also given. No SDK versions are pinned. Requirements: Python 3.9+ or Node 18+. | M-qs |
| Protocols | Responses (`/v1/responses`, recommended for tools and agents), Chat Completions, and an Anthropic-style Messages API | M-idx, M-tool, M-mod |
| Rate limits | Per **team**, per model (tables in each model section below). 429s come with an optional `Retry-After`. Successful token-model responses carry `x-ratelimit-limit/remaining-tokens/requests` headers. Use exponential backoff with jitter starting around 500 ms. Background (`background: true`) submissions are capped at 600/min/team. | M-price |
| Pricing page | https://dev.meta.ai/docs/pricing-rate-limits. No separate billing doc; the Dashboard is at `/platform`. | M-price |
| Billing mechanics | A team admin adds the payment method. You're charged when the balance hits a payment threshold, and the remainder on the 1st of each month. "Pay now" pays early. (This is documented on the Muse Code billing page, and appears to describe the shared Model API account: **VERIFY** that it applies to plain API use.) | M-mc-auth |
| Usage reporting (per run logging) | **Responses:** `usage.input_tokens`, `output_tokens`, `total_tokens`, `input_tokens_details.cached_tokens`, `output_tokens_details.reasoning_tokens`. **Chat Completions:** `prompt_tokens`, `completion_tokens`, `total_tokens`, `prompt_tokens_details.cached_tokens`, `completion_tokens_details.reasoning_tokens`. Reasoning tokens are a subset of output and are billed at the output rate. When streaming on Chat Completions, set `stream_options: {"include_usage": true}`; on Responses, read `usage` from the final response. With hosted tools, `input_tokens` is cumulative across iterations. **There is no per-request cost field**, so compute cost as usage x price table. | M-tok, M-reas, M-qs |
| Pre-flight token count | `POST /v1/responses/input_tokens` (records no usage). Meta says to use it for context fit, not billing estimates. | M-tok |
| Files API | `POST /v1/files`, `purpose=user_data`. 50 MB inline, 1 GiB upload, 100 GiB team storage. No expiry by default (`expires_after` 1 h to 30 d). Types: PNG/JPEG/GIF/WebP/ICO, **MP4 only** for video, MP3/WAV, PDF, text/JSON/JSONL. Up to 50 images per request. | M-file |
| Hackathon Meta credits | **VERIFY.** No credits are mentioned on any Meta docs page or on CV1. The $150 figure comes from Meta's Oct 13 announcement email. | M-price, M-ov, CV1 |
| Contributor vs Standard | In Contributor mode Meta may train on your content; in Standard it does not. **CHANGED (clarified):** Contributor is available only for Muse Spark (1.3 and 1.2), not for Wonder, Image, or Voice Transcribe. | M-price, M-mod |

**EmberScan logging recipe (inference):** for each call, store `{model, endpoint, input_tokens, cached_tokens, output_tokens, reasoning_tokens}`. For SAM, store the frame count (with a minimum of 50 per video request), for Image the image count, and for Voice the billed seconds. Multiply by the M-price table, which you keep as a config constant.

---

## 2. Muse Spark (all listed versions)

| Field | `muse-spark-1.3` | `muse-spark-1.3-contributor` | `muse-spark-1.2` | `muse-spark-1.2-contributor` | `muse-spark-1.1` | Source |
|---|---|---|---|---|---|---|
| Status | Recommended for new work | 1.3, Contributor | Previous | 1.2, Contributor | Original, Standard only | M-mod |
| Context | 1,048,576 | 1,048,576 | 1,048,576 | 1,048,576 | 1,048,576 | M-mod |
| Input | Text, image, video, audio, PDF (audio "not fully supported", so use 1.2 for audio) | same | Text, image, video, audio, PDF | same | same | M-mod, M-vid |
| Output | Text | Text | Text | Text | Text | M-mod |
| Reasoning effort | `minimal` to `max` | up to `xhigh` (no `max`) | **VERIFY** per-level list | **VERIFY** | **VERIFY** | M-reas, M-mod |
| Price per 1M (input / cached / output) | $1.25 / $0.15 / $4.25 | $0.10 / $0.002 / $0.20 | $1.25 / $0.15 / $4.25 | $0.10 / $0.002 / $0.20 | $1.25 / $0.15 / $4.25 | M-price |
| Rate limit | 3,000 RPM / 4M TPM | 150 RPM / 3M TPM | 3,000 / 4M | 150 / 3M | 3,000 / 4M | M-price |
| Latency | **VERIFY** (none published) | | | | | none |

Web search grounding costs $2.50 per 1,000 queries on top of tokens (M-price). Reasoning: `"none"` returns 400 on Spark and Wonder. The parameter is `reasoning.effort` on Responses and `reasoning_effort` on Chat Completions. Omitting it gives a model-chosen default (M-reas).

### 2a. Structured output (JSON schema)

| Field | Value | Source |
|---|---|---|
| Responses | `text.format` with a JSON schema | M-so |
| Chat Completions | `response_format: {type: "json_schema", json_schema: {...}}`. Pydantic works through `client.beta.chat.completions.parse()`. | M-so |
| Enforcement | **Constrained decoding**, with output conforming even at `strict: false` (the default). `strict: true` only adds server-side schema validation against the strict subset: object root, no `allOf`/`oneOf`, `additionalProperties: false`, and all keys required. | M-so |
| Limits | Depth 10, 5,000 properties, 1,000 enum values, 200k nodes after `$ref`. **Recursive schemas are rejected (400).** These limits also apply to tool `parameters`. | M-so |
| `json_object` mode | Not documented: **VERIFY** | M-so |
| Models covered | Examples use only `muse-spark-1.3`. Support on 1.1, 1.2 and Contributor variants: **VERIFY** | M-so |

### 2b. Tool / function calling (for the EmberScan agent)

| Field | Value | Source |
|---|---|---|
| Recommended API | Responses API (Chat Completions is also fully supported) | M-tool |
| Tool definition | Responses: **flat** `{type:"function", name, description, parameters, strict?}`. Chat Completions: nested under `function`. `type:"custom"` (freeform text) works on Responses only. | M-tool |
| Call / result loop | Responses: `output[]` holds `function_call` items (`name`, `arguments`, `call_id`). Reply with `function_call_output` items carrying the matching `call_id`, usually with `previous_response_id`. Chat Completions: `tool_calls` with `finish_reason:"tool_calls"`. Append the full assistant message, then one `role:"tool"` message per call with its `tool_call_id`. Leaving out the assistant message returns 400. | M-tool |
| `tool_choice` | **NEW / important: only `"auto"` is supported.** `"none"`, `"required"`, and named functions all return 400. You cannot force a specific tool, so steer through the prompt and validate. | M-tool |
| Parallel calls | `parallel_tool_calls` defaults to `true` | M-tool |
| Strict | Defaults to `false`. With `true` the schema must fit the strict subset. Always validate arguments yourself. | M-tool, M-so |
| Naming | `^[a-zA-Z0-9_.-]+$`, at most one dot. `call_id` 1 to 64 chars. | M-tool |
| Many tools | `defer_loading: true` plus the `tool_search` tool | M-tool |
| Streaming | Responses: `response.function_call_arguments.delta` / `.done`. Chat Completions: accumulate `tool_calls` by `index`. | M-tool |
| Models | Examples use `muse-spark-1.3`. Wonder: "any Muse Spark example works" by swapping the ID. Contributor variants and 1.1: **VERIFY**. | M-tool, M-ov |

EmberScan tool set (inference): `get_segmentation(concept, clip_id)`, `measure_distance(track_a, track_b)`, `evaluate_rules(state, zone, findings)`, `lookup_fix_cost(item, region)`. Keep the schemas flat, since recursive schemas are rejected.

### 2c. Image / video input

| Field | Value | Source |
|---|---|---|
| Image | JPEG/PNG/GIF/WebP/ICO by URL, data URL, or `file_id`. User messages only. 50 per request, 50 MB inline. No stated max pixels; the model may resize. About 1,300 to 1,500 tokens for a roughly 1280 px image. | M-img |
| Video | MP4 through `input_file` (file_id, recommended), `input_video` (`file_id` or `video_url`), or the Chat Completions `video_url` part. **Muse Spark reads the embedded audio track along with the frames.** | M-vid |
| Max duration / fps / tokens per second | **VERIFY** (not documented) | M-vid |
| MOV for Spark | Not listed (MP4 only). Remux MOV to MP4 (inference). | M-vid, M-file |
| Transcription caveat | Set max output to at least 4,000 tokens, or reasoning can starve the transcript (`finish_reason: length`) | M-vid |

---

## 3. SAM 3.1 (`sam-3.1`)

| Field | Value | Source |
|---|---|---|
| Endpoint | `POST /v1/responses`, same Bearer key, `stream: true` recommended for video | M-sam-ov, M-sam-seg |
| Video vs frames | One model for both. Image uses an `input_image` part (URL or data URL). Video uses an `input_video` part (`video_url` or `file_id`). **Send the whole clip as video** to get tracking. Individual frames as images get no cross-frame IDs (inference from the per-image output). | M-sam-seg |
| Containers / codecs | MP4 or MOV with H.264/H.265/MPEG-4. VP9/WebM rejected. Use `-movflags +faststart` to skip the server remux. | M-sam-seg |
| Max length | 15,000 frames (about 10 min) per request | M-sam-seg |
| Max resolution / fps / file size | Resolution and fps: **VERIFY** (not documented; there is no fps or stride parameter, and frame markers can skip). File size: the general 50 MB inline / 1 GiB Files API limits apply. | M-sam-seg, M-sam-read, M-file |
| Concept (text) prompts | A short noun phrase ("bark mulch", "wood fence"). **One concept per request.** Lists, OR, negation, spatial terms and questions are unreliable or return zero. Case and plurals don't matter. | M-sam-seg |
| Box / point prompts | `<Nf>id<\|box;x1;y1;x2;y2;w;h\|>` and `<\|point;x;y;w;h\|>` (prefix `-` for a negative point). `w`/`h` must equal the displayed media size. Images use frame 0. You can't mix with a concept prompt in one request. Up to 16 prompted objects. | M-sam-seg |
| Object limits | Images: every match. Video: up to 16 tracked objects per frame. | M-sam-seg |
| Tracking IDs | Stable within one response. Not reliable across exit/re-entry, full occlusion, or very long clips. IDs are sparse, so key by ID. `metadata.propagation_direction`: `both` (default) / `forward` / `backward` (box/point). | M-sam-read, M-sam-seg |
| Output format | Special-token text in `output_text`, one `response.output_text.delta` per frame: `<Nf>id<\|box;...\|><\|mask;x=0;y=0;data=H,W,<~or!>base85\|>`. Boxes are in source pixels; masks are lower-res. Empty frames emit no line. Zero matches gives empty output, not an error. Concept-prompt frames ascend; box/point frames follow the propagation order. | M-sam-read |
| Confidence | `metadata.include_confidence: "true"` (a **string**) adds `c` from 0 to 1 per box and mask, **per frame** | M-sam-seg, M-sam-read |
| Mask encoding | `metadata.mask_encoding`: `lossless` (default) or `one_bit` (several times smaller). Box/point prompts always return one_bit. | M-sam-seg |
| Parser libs | npm **`@meta-sam/parser` 0.1.0** (latest; license "SEE LICENSE IN LICENSE") plus optional `@meta-sam/graphics`, `@meta-sam/video`, `@meta-sam/react`. ESM only, Node `^20.17` or `>=22.9`. PyPI **`meta-sam-parser` 0.1.0** (import `meta_sam_parser`, SAM License, Python >= 3.10, zero deps, uploaded 2026-10-06). Confidence needs npm 0.0.13+ / py 0.0.6+. **NEW:** box/point prompt builders need 0.1.0+. Functions: `parseVideoStream`, `parseImageStream`, `parseResponsesStream`, `decodeMaskToRaster`, `decodeMaskToRLE`, `decodeMaskToSVGPath`, `buildObjectPrompt`. The Python entry-point names for parsing are **VERIFY**. | M-sam-lib, NPM-sam, PYPI-sam |
| Pricing | $2.50 per 1,000 images, or $0.20 per 1,000 video frames. **NEW: each video request bills at least 50 frames.** | M-price |
| Rate limit | 3,000 RPM, no TPM limit | M-price |
| Latency | **VERIFY** (none published by the hosted API or the cookbook) | M-sam-ov, M-sam-cb |
| Errors | 400 for invalid prompt or metadata (don't retry unchanged). 404 `model_not_found`. | M-sam-seg |

**Cost note (inference):** cost scales with frames x concepts. For example, a 3 min clip at 30 fps is 5,400 frames, about $1.08 per concept, so 5 concepts cost about $5.40. Since there's no fps parameter, re-encode to a lower fps with ffmpeg before upload to cut frames. Map frame index to time as `frame / fps_of_uploaded_file`.

---

## 4. Muse Voice Transcribe (`muse-voice-transcribe-1.0`): **NEW** (newly documented)

| Field | Value | Source |
|---|---|---|
| Endpoints | File: `POST https://api.meta.ai/v1/asr/transcribe` (multipart: `request` JSON part plus `audio` part, Bearer header). Realtime: `wss://api.meta.ai/v1/asr/realtime` (token in the handshake `authorization.accessToken`). | M-stt, M-mod |
| Audio formats | File endpoint: **WAV only**: RIFF/WAVE, mono, 16-bit PCM, 16 kHz or 24 kHz. Realtime: raw s16le mono PCM, 24 kHz preferred. | M-stt, M-stt-api |
| MP4/MOV input? | **No.** Video isn't mentioned, so **extract the audio**, e.g. `ffmpeg -i walk.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le walk.wav` (the docs show an equivalent ffmpeg conversion for .m4a). | M-stt |
| Limits | 32 MB body (413), **10 min max audio** (400), 60 min realtime session, 256 concurrent streams, 16,000 streams/hour. 429 or close code 1013 means back off. | M-stt, M-price |
| Timestamps | **Turn-level only**: `turns[]` with `turnId`, `startMs`, `endMs`, `transcript`, `speaker`. **No word-level timestamps** and no confidence scores. | M-stt, M-mod |
| Alignment to frames (inference) | Use turn `startMs`/`endMs` x fps to get a frame range per narration turn. Use `ENDPOINTING` mode to get finer turns. For finer alignment, keep turns short (the narrator pauses between features). | M-stt |
| Modes | `PUSH_TO_TALK` (default), `ENDPOINTING`, `DIARIZATION` | M-stt |
| Languages | 25, with code-switching: Arabic, Bengali, Dutch, English, French, German, Hebrew, Hindi, Indonesian, Italian, Japanese, Kannada, Korean, Malay, Mandarin, Marathi, Polish, Portuguese, Spanish, Tagalog, Tamil, Telugu, Thai, Turkish, Vietnamese. `languageBias` and `keywords` (e.g. "defensible space", "Zone 0") are set at session start. | M-stt |
| Response formats | `application/json` (default), `text/event-stream`, `text/plain` | M-stt |
| Pricing | **$0.18 per audio hour**, billed per whole second (rounded down). Failed requests and 429s are not billed. No Contributor mode. | M-price, M-stt |
| Rate limit | No RPM/TPM; stream limits above. No `x-ratelimit-*` headers. | M-price |

---

## 5. Muse Image (`muse-image-1.0`)

| Field | Value | Source |
|---|---|---|
| Endpoints | `POST /v1/images/generations` (text to image), `POST /v1/images/edits` (image to image / compose), and `POST /v1/responses` (multi-turn refinement with `previous_response_id`) | M-imgen |
| Editing a real frame | Supported: `images` holds 1 to 10 items (`image_url` URL/data URL or `file_id`); the OpenAI SDK sends multipart `image`. **No masks** (`mask` returns 400 `unsupported_parameter`), so the region to change must be described in the prompt, e.g. "replace the bark mulch bed along the wall with gray gravel; keep everything else identical". The cookbook "Edit image details across turns" recipe says to check that unchanged areas still match the source. | M-imgen, M-imgcb |
| Params | `prompt` (required; max length **VERIFY**), `n` 1 to 10, `size` "WxH" sets **aspect ratio only** (default `auto`, more than 16:1 rejected), `response_format` `b64_json`/`url`, `output_format` `webp` (default)/`png`/`jpeg`, `reasoning_strength` `high` (default)/`low` (single pass, faster), tool flags `enable_image_search` / `enable_web_search` / `enable_shell` (all on by default), `stream`, `user`/`safety_identifier`. **NEW:** `moderation` returns 400 if set. | M-imgen |
| Inputs | Image URL inputs must serve an `image/*` Content-Type | M-imgen |
| Output resolution | Not guaranteed to match `size`; no list given: **VERIFY** | M-imgen |
| Safety | A blocked prompt returns 400 `content_policy_violation`. Real-person or photo-editing rules: **VERIFY** (not documented). | M-imgen |
| Watermark / provenance | **VERIFY** (not mentioned) | M-imgen |
| Pricing | $0.01 per returned image, flat (reasoning and tools don't change it). Failed or safety-removed images aren't billed. | M-price, M-imgen |
| Rate limit | 150 RPM | M-price |
| Latency | **VERIFY**. `reasoning_strength: low` and disabling tools are documented as faster. | M-imgen |

Product note (inference): label every after-image as an AI visualization, not a measurement. Disable `enable_web_search`/`enable_shell` for frame edits.

---

## 6. Muse Wonder (`muse-wonder-1.0`)

| Field | Value | Source |
|---|---|---|
| What it is | Meta's most capable model, **in preview**: "complex software engineering and long-horizon agentic work", multi-file repo changes, sub-agents, and parallel tool calls. Any Spark example works by swapping the model ID. | M-ov, M-mod |
| Context / IO | 1,048,576 tokens. Text, image, video, audio and PDF in; text out. Effort `minimal` to `max`. | M-mod |
| Wonder Full | Muse Code Power/Maximum plans only; not on the API | M-mod, M-mc-sub |
| Pricing | $4.00 / $0.20 cached / $20.00 output per 1M tokens. No Contributor mode. | M-price |
| Rate limit | 3,000 RPM / 4M TPM | M-price |
| Geography | Not available in South Korea | M-mod |
| Adds anything for EmberScan? | **Little.** Our agent loop is short (a few tool calls over segmentation, measurement, rules and cost). Output tokens cost 4.7x Spark 1.3 and the model is a preview. Possible use: a one-off A/B on hard rule-interpretation cases, or through Muse Code for development. (Inference.) | M-price |

---

## 7. Open-weight models

### 7a. Licenses

| Model | License | Attribution | Other terms | Source |
|---|---|---|---|---|
| Muse Spark Open (816B MoE, 42B active, 1,048,576 ctx; text/image/audio/video in) | **Muse Model License** (Muse Spark Open version, **dated 2026-10-15**) plus the Acceptable Use Policy | **Must prominently display "Built with Muse Spark Open"** in the product UI, or in docs, website or settings | Commercial use free. Model-as-a-Service above $20M revenue in 12 months needs a separate Meta agreement. Not for under-18s. Meta claims no ownership of outputs. HF weights are gated (legal name, DOB, org). | HF-mso, M-mso |
| Muse Glimmer (30B dense; text and image in; 128K default ctx, longer supported) | **Apache 2.0** plus USAGE_POLICY.md | No required phrase (citation requested, not required). Apache 2.0's own NOTICE/license-copy rules apply if redistributing. | Not gated. No audio. Not for under-18s. | HF-mg, M-mg, M-mg-get |

### 7b. Calling them on partners

| | **Baseten** | **Modal** | **Fireworks** | Source |
|---|---|---|---|---|
| Muse Spark Open model ID | Public slug `meta-models/muse-spark-open`. **The hackathon ID `meta-models/muse-spark-open-1026` does not appear on any public Baseten or Meta page today: VERIFY** with `GET https://inference.baseten.co/v1/models` once the credits post (free; no inference). | `meta-models/Muse-Spark-Open-816B-A42B` (Shared Endpoint, NVFP4) | `accounts/fireworks/models/muse-spark-open` | BT-lib, BT-price, BT-api, MD-lib, FW-mso, M-mso-dep |
| Endpoint | `https://inference.baseten.co/v1` (Chat Completions). Messages API in beta at `https://inference.baseten.co`. | Per-endpoint URL from the dashboard; `/v1/chat/completions`, `/v1/responses`, `/v1/messages`, `/v1/models` | `https://api.fireworks.ai/inference/v1` | BT-api, MD-ep, FW-fc, M-mso-dep |
| Auth | `Authorization: Bearer $BASETEN_API_KEY` | `Authorization: Bearer wk-<id>.ws-<secret>` proxy token (`modal workspace proxy-tokens create`). Optional `Modal-Routing-Affinity-Key`. | Bearer `FIREWORKS_API_KEY` (raw header not shown; the OpenAI client is used) | BT-api, MD-ep, FW-fc |
| OpenAI compatible | Yes (change base URL, key, model) | Yes (Chat Completions and Responses) | Yes | BT-api, MD-ep, FW-fc |
| Tool calling | Yes, "all Model APIs" | Model page claims tool use; API params not documented: **VERIFY** | Yes (model page). `tool_choice` auto/none/required/named. | BT-api, MD-lib, FW-mso, FW-fc |
| Structured output | **NEW: Muse Spark Open "accepts `json_schema` but doesn't enforce the schema"**, so use tool calls plus validation instead | Not documented: **VERIFY** | `response_format` json_schema documented generally; per-model support **VERIFY** | BT-so, BT-api, FW-fc |
| Context | 1,048,576 (Meta deploy page). Media over about 74 MB must go by URL. | 1M | 1,040k | M-mso-dep, MD-lib, FW-mso |
| Price per 1M (input / cached / output) | $1.25 / $0.15 / $4.25 | $1.25 / $0.15 / $4.25 | $1.25 / $0.15 / $4.25 (serverless, US capacity) | BT-price, MD-lib, FW-mso |
| Rate limits | Account defaults: Basic unverified 15 RPM / 100k TPM, verified 120 / 500k, Pro 120 / 1M. Hackathon: **2M TPM** (CV1). Keep around 60 RPM per session. | **VERIFY** | Serverless **VERIFY**; dedicated "no rate limits" | BT-rl, BT-api, CV1, FW-mso |
| Usage reporting | `baseten model-api usage`, `GET /v1/model_apis/usage`, Prometheus metrics; 92-day retention; enforceable monthly budget | **VERIFY** | **VERIFY** | BT-rl |
| Quirks | `n>1` returns 400; logprobs ignored; no determinism | none found | `reasoning_effort` defaults to `xhigh`; `"none"` rejected | BT-api, M-mso-dep |
| Muse Glimmer | **Not listed** on the Baseten pricing page: **VERIFY** (it was listed earlier) | **Dedicated Endpoint only** (`meta-models/Muse-Glimmer-30B`, BF16 and NVFP4 pages), per-second compute billing, function calling listed | `accounts/fireworks/models/muse-glimmer-30b`, 131k ctx, function calling. **Serverless ended 2026-09-25**; on-demand dedicated GPUs only. | BT-price, MD-mg, FW-mg |
| Partner credit | $100 plus 2M TPM ("select participants") | $100 for Endpoints ("select participants") | $25 ("select participants") | CV1 |

Other Muse Spark Open hosts listed by Meta: Together, Groq (approval needed, 131k ctx), Nebius, OpenRouter (M-mso-dep). Glimmer's only Meta-listed hosted provider is Together AI serverless at $0.35 / $1.50 per 1M (M-mg-dep), which is not an event partner. Self-host parser flags: vLLM `--tool-call-parser muse --reasoning-parser muse --enable-auto-tool-choice` (Spark Open), and `muse_glimmer` for Glimmer on vLLM (M-mso-dep, M-mg-dep).

### 7c. "Best Build on Meta Open-Weight Models" prize

**VERIFY.** The prize is not named on CV1 or on any Meta docs page, and a web search found nothing. It is probably in the login-gated participant guide (CV2) or the Official Rules. CV1 still says Official Rules "will be published before the Hackathon begins on October 26" and shows no link to them. Ask: does the prize require open weights for the core agent, does SAM 3.1 count, and does the required "Built with Muse Spark Open" UI attribution satisfy any disclosure rule?

---

## 8. Muse Code

| Field | Value | Source |
|---|---|---|
| What it is | Meta's terminal and CI coding agent built for Muse Spark. It plans, edits and runs commands, with approvals and an OS sandbox on by default. Supports headless use (`muse exec`) and a TS SDK `@muse-code/sdk`. | M-mc |
| Install | Windows `irm https://dev.meta.ai/install.ps1 \| iex`; macOS/Linux `curl -fsSL https://dev.meta.ai/install.sh \| sh`; check with `muse --version` (not installed during this research) | M-mc, M-qs |
| Auth | Browser sign-in or API key. `META_API_KEY` (env) takes priority over a stored key, which takes priority over a browser session. `muse auth set`, `muse logout`, `/login`. Meta Managed Account users must use an API key. | M-mc-auth |
| Default model | `muse-spark-1.2` | M-mc |
| Billing | Pay-as-you-go per token on a Model API key, **or** a subscription: Everyday (10 to 50 prompts per 5 h, includes Spark, Wonder, Image), High (5x), Power (20x, adds Wonder Full), Maximum (80x). **Prices are not listed** ("shown during onboarding"): **VERIFY** | M-mc-sub, M-mc-auth |
| Windows | Uses PowerShell; the sandbox may show a UAC prompt; no voice or session messaging | M-mc |
| Hackathon access | **VERIFY.** Not on any docs page. CV1 says only "code faster with Muse Code coding agent". Meta's Oct 13 announcement email said participants get Muse Code access. | CV1 |

---

## 9. Recommended model per job (EmberScan)

Spend is on a personal card until credits post, so the cheapest sensible development choice comes first.

| Job | Dev choice (cheap) | Demo / prod choice | Why | Source |
|---|---|---|---|---|
| Agent brain (tool loop over segmentation, measurement, rules, cost) | `muse-spark-1.3-contributor` **only with our own test walkarounds** (no homeowner footage, since Meta may train on it); `reasoning.effort: "low"` | `muse-spark-1.3` Standard, effort `medium` | 12x cheaper input and 21x cheaper output in dev. Responses API flat tools. Remember `tool_choice` is auto-only. Contributor is capped at 150 RPM, which is fine for dev. | M-price, M-tool, M-reas |
| Explanations / report text | Same as above; `text.format` JSON schema for report sections | `muse-spark-1.3` | Constrained decoding means the JSON always parses | M-so |
| Segmentation and tracking | `sam-3.1` on short trimmed clips, lowered fps, `one_bit` masks, one request per concept | `sam-3.1`, full walkaround up to 10 min, `include_confidence:"true"` | $0.20 per 1k frames (50-frame minimum). Stable IDs within a request. Parse with `@meta-sam/parser@0.1.0`. | M-price, M-sam-seg, NPM-sam |
| Narration transcript and alignment | `muse-voice-transcribe-1.0` on ffmpeg-extracted 16 kHz mono WAV, `ENDPOINTING` mode | same | $0.18/hr. Turn-level `startMs`/`endMs` map to frames. No word timestamps. Clip at 10 min / 32 MB. | M-stt, M-price |
| "After" visualization of a fix | `muse-image-1.0` `/v1/images/edits`, `n:1`, `reasoning_strength:"low"`, tools off | same, `reasoning_strength:"high"` | $0.01 per image; there's no mask, so describe the region in the prompt | M-imgen, M-price |
| Open-weight path (prize) | Muse Spark Open on **Baseten** (`meta-models/muse-spark-open`, slug `-1026` **VERIFY**), using partner credits only; no personal spend until credits post | same, plus "Built with Muse Spark Open" in the UI | Same price as Spark 1.3 Standard, 2M TPM hackathon limit, tool calling supported. Its JSON schema is **not enforced**, so validate. Fireworks ($25) is the backup. | BT-lib, BT-api, BT-so, CV1, HF-mso |
| (Skip) | Muse Wonder | none | 4.7x the output cost and in preview; no clear win for a short tool loop | M-price, M-ov |

---

## 10. Recently changed or newly documented

1. **NEW:** Muse Voice Transcribe (`muse-voice-transcribe-1.0`, $0.18/hr, WAV-only file API, 10 min / 32 MB, turn-level timestamps only) is documented and is newly documented.
2. **NEW:** SAM video bills at least 50 frames per request.
3. **NEW:** SAM parsers are now at **0.1.0** (npm and PyPI), and box/point prompt builders need 0.1.0+.
4. **NEW:** Tool calling accepts `tool_choice: "auto"` only. Strict defaults to false. Structured output uses constrained decoding . Recursive schemas are rejected.
5. **NEW:** Usage fields and the `/v1/responses/input_tokens` endpoint are documented. There is no cost field.
6. **CHANGED:** Contributor mode is explicitly Spark-only. Muse Image now rejects `moderation`.
7. **NEW:** Baseten does not enforce `json_schema` for Muse Spark Open. Baseten tier rate limits and usage API are documented.
8. **CHANGED:** Fireworks Glimmer serverless ended 2026-09-25. Modal offers Glimmer only as a Dedicated Endpoint. Glimmer is no longer seen on Baseten's pricing page.
9. **CHANGED:** Muse Model License is now dated 2026-10-15, and the "Built with Muse Spark Open" wording is reconfirmed.
10. **CHANGED:** The participant guide is now login-gated. Official Rules are still not linked on CV1.

## Summary

**Confirmed (2026-10-26):** The Meta Model API runs at `https://api.meta.ai/v1` with Bearer `MODEL_API_KEY`, OpenAI SDK compatibility, per-team limits, and usage token fields for cost logging. Muse Spark 1.3/1.2/1.1 (plus Contributor) has 1M context, constrained-decoding JSON schema, and flat Responses tools with auto-only `tool_choice`. SAM 3.1 takes MP4/MOV clips up to 15k frames, one concept per request, with stable track IDs, base85 masks, and `@meta-sam/parser` / `meta-sam-parser` 0.1.0, at $0.20 per 1k frames (50 minimum). Voice Transcribe takes WAV only, gives turn timestamps, and costs $0.18/hr. Muse Image edits without masks for $0.01. Licenses: Muse Model License (attribution "Built with Muse Spark Open") and Apache 2.0 for Glimmer. Muse Spark Open costs $1.25/$4.25 on Baseten, Modal and Fireworks.

**Changed:** See section 10 (Voice Transcribe added, SAM 50-frame minimum, parser 0.1.0, auto-only tool choice, Baseten schema not enforced, Glimmer hosting narrowed, guide login-gated).

**Still VERIFY:** the Baseten `-1026` slug; the open-weight prize criteria; Meta credits; Official Rules; Muse Code prices and hackathon access; SAM resolution, fps and latency; Spark video duration limits; Muse Image prompt length, resolution, watermark and real-photo rules; Modal and Fireworks rate limits.

## 11. First live checks (2026-10-26)

- `GET /v1/models` with our key returned: muse-image-1.0, muse-spark-1.1, muse-spark-1.2, muse-spark-1.2-contributor, muse-spark-1.3, muse-spark-1.3-contributor, muse-voice-transcribe-1.0, muse-wonder-1.0, sam-3.1. All models we plan to use are available on this account.
- `POST /v1/responses` on `muse-spark-1.3-contributor` with `reasoning.effort: "low"` and `max_output_tokens: 16` returned 200 in 2.7 s with an **empty reply**: 14 of the 16 output tokens were reasoning tokens. **`max_output_tokens` includes reasoning tokens**, so always leave headroom (at least a few hundred tokens for agent steps) and treat an empty message as a retryable error.
- SAM 3.1, Voice Transcribe and Muse Image are checked on Day 2 with real footage.
