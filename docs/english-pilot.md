# English original-source pilot

This opt-in path reuses the existing English router and model gateways in a minimal FastAPI app, `src/english_app.py`. Its separate collection contains **14 complete original-source contexts**, split into 61 discovery windows. It is a bounded experiment, not the complete Buffett archive or an accepted production release. Read the recorded answer-quality results separately; a running server and working citations do not establish semantic accuracy.

The launcher does not call `start.py`, `ingest_md.py`, or the legacy corpus ingestion flow. `serve` requires a compatible existing pilot index and fails before opening a port if it is missing. Only the explicit `index` action builds that index.

## Server configuration

Install `requirements.txt` in the intended Python environment first. For local use, create a private `.env` from `english-pilot.env.example` in a fresh checkout, and replace the API-key placeholder. Do not overwrite an existing secret/configuration file. On Railway, supply the same variables as service secrets/environment variables; do not put a real key in a command, Git commit, browser, or Docker image.

The current preview configuration is below. It remains experimental: recorded source reviews, rather than the model name or a successful request, determine acceptance.

| Setting | Value |
| --- | --- |
| API endpoint | `https://openapi.wtsht.cn/v1` |
| Generation provider/model | `openai_compatible` / `GLM-5.3-Flash-W8A8` |
| Generation timeout/retries | 110 seconds / 0 |
| Generation route | `knowledge_answer`, primary `default`, no fallbacks |
| Generation output/temperature | 12,000 token limit per model pass / 0.2 |
| Extra provider body | `thinking.type=enabled`, `reasoning_effort=high` |
| Embedding provider/model | `openai_compatible` / `Qwen3-Embedding-8B` |
| Embedding timeout/retries | 45 seconds / 0 |
| Embedding batch size/dimension | 32 / 4,096 observed dimensions |
| API-key environment variable | `AI_API_KEY` for both gateways |
| Pilot enabled | `ENGLISH_PILOT_ENABLED=true` |
| Legacy ingestion | `AUTO_INGEST=false` |
| Pilot call limit | `ENGLISH_PILOT_CALL_LIMIT=40` in the example; an explicit finite allocation |

For an explicit route configuration, use this server environment value:

```json
{"knowledge_answer":{"primary":"default","fallbacks":[],"max_tokens":12000,"temperature":0.2}}
```

Set it as `AI_TASKS_JSON`. Remove conflicting `AI_TASK_KNOWLEDGE_ANSWER_*` overrides from this pilot service's configuration. The sample's `AI_PROFILES_JSON` supplies the exact generation profile with zero retries; `AI_MODEL` alone would use gateway retry defaults and is insufficient.

Existing `database/ai_settings.json` settings take precedence over environment profiles. Do not silently delete or replace a previous service's settings to make this pilot start. Use an isolated pilot database volume, or deliberately reconcile those settings before switching a service. The launcher rejects effective profiles with retries or generation fallbacks.

Local `.env` values take precedence over process variables, matching `server.py`. Avoid a `.env` in a hosted image. `--port` takes precedence over `PORT`; without either the port is 8802. Listening beyond loopback always requires an explicit `--host` argument.

## Local: three commands

Run from the repository root after the dependency and secret setup:

```sh
python scripts/english_pilot.py index
python scripts/english_pilot.py status
python scripts/english_pilot.py serve --port 8802
```

Open `http://127.0.0.1:8802/`. The default bind address is `127.0.0.1`. `status` validates the index against the active corpus and embedding profile and prints non-secret model/index information. It does not call a model. `serve` performs the same preflight and starts one Uvicorn worker with `english_app.app`; it does not rebuild anything or import the full legacy `server.app`.

For CLI help without application imports or network access:

```sh
python scripts/english_pilot.py --help
```

## Railway: persistent storage and explicit startup

The current Dockerfile uses `/app` as its working directory. Mount a persistent volume at **`/app/database`** before building the pilot index. That directory must retain the Chroma collection, `buffett_english_contexts_v1.json` manifest, and `english_pilot.sqlite3` request/call ledger together across restarts. The image excludes `database/`; an index built only on a laptop is not available in the deployed container.

Keep one service instance and one Uvicorn worker for this pilot. Its concurrency semaphore is process-local; it is not a distributed queue. Set the server configuration above, keep `AUTO_INGEST=false`, and override the service start command to use the pilot launcher instead of the image's `python start.py` default.

The hosted three-command sequence, executed in the deployed runtime with its mounted volume, is:

```sh
python scripts/english_pilot.py index
python scripts/english_pilot.py status
python scripts/english_pilot.py serve --host 0.0.0.0
```

Railway supplies `PORT`; the last command reads it without requiring shell variable expansion. Running these commands on a local machine with hosted environment variables still creates a **local** database, not the Railway volume.

On the first boot of an empty volume, explicitly configure this temporary start command if a separate one-off container command is unavailable:

```sh
python scripts/english_pilot.py index && python scripts/english_pilot.py serve --host 0.0.0.0
```

This authorizes a finite indexing action: the current 61 windows use **two embedding requests** with batch size 32. Indexing has no hidden retry. A later run with the same complete index and manifest validates/reuses it without new embeddings. An incompatible existing manifest is rejected rather than overwritten. A failed partial first build may require another explicit indexing attempt; its earlier calls remain charged in the ledger.

After successful initialization, use the normal start command:

```sh
python scripts/english_pilot.py serve --host 0.0.0.0
```

The dedicated `/health` route returns HTTP 200 when the pilot index matches the current sources/model, and HTTP 503 when it is missing or incompatible. It explicitly reports index readiness only, without calling a paid model. Also inspect `/api/english/status` and exercise a new free-form question, its citation cards, and stream completion. A health check alone does not validate model access or answer quality. No deployment is performed by this documentation or by `status`.

## Bounds and deployment limitations

The SQLite ledger counts reserved provider attempts, including failures, against the configured **absolute** pilot limit. It is not a daily limit or a verified currency budget. Each question uses one query-embedding call and one writer call. With `ENGLISH_PILOT_VERIFY=true` (explicitly enabled in the example), it uses one additional model call to check and correct the draft against the same originals. This optional second pass has no separate source search, planner, or retries. Its existence does not certify the answer. With the flag false, the single-pass baseline remains available. There is no generation fallback or SDK retry. Unknown token usage remains unknown, and actual token charges must be reconciled with the provider. Do not delete the ledger or replace the volume to renew the allowance. Raising a finite limit preserves existing rows and counters; previous project experiments have separate historical records.

The English UI labels streamed text as a draft until completion. During the optional source check it retains the draft and shows the checking status; only a complete corrected response replaces the draft. A failed check leaves the draft incomplete. Mechanical reference checks do not prove that a claim follows from an original. Incomplete streams and flagged references must remain visible as such; successful transport is not editorial acceptance.

The dedicated launcher exposes only the English router, its homepage, and `/health`. Legacy model-settings, coach, tutor, and Q&A routes are not mounted. The opt-in English path inside the full `server.py` app remains for compatibility, but launching that full app also retains its unrelated endpoints; use the dedicated launcher for this hosted pilot.

**This remains a bounded single-user test, not a public authentication or per-user-quota product.** The service has a shared call ledger and one in-process concurrency slot. `ENGLISH_PILOT_ENABLED=true` and same-origin checks do not make a service private. Use a controlled preview with external access restrictions before exposing a hosted address; do not treat this branch as ready for anonymous public traffic. No new authentication system is introduced here.

## Reproduce the live question checks

Run only explicit cases, for example `python scripts/evaluate_english_pilot.py V0 O1 C1`. Each case makes paid calls according to the selected mode. Results are saved under ignored `database/evaluation/`, with actual source contexts, model usage and timing. They are observations, not automatic semantic pass scores.

The GLM reasoning controls follow the [vendor’s thinking-mode documentation](https://docs.bigmodel.cn/cn/guide/capabilities/thinking); MarsAPI is a separate compatible endpoint, so behavior and latency must be measured there.
