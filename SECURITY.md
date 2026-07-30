# Security

IncidentPilot is a personal portfolio project intended to run locally. It is not
hardened for production or for deployment on an untrusted network.

## Reporting

Open an issue on the repository. There is no private disclosure process and no
support commitment.

## Threat model

The agent consumes a Prometheus alert delivered to an unauthenticated webhook and
feeds that content to an LLM that can call tools. Alert content is therefore
treated as untrusted attacker-controlled input throughout.

Authentication on the FastAPI endpoints is deliberately out of scope for this
project. The mitigation is network isolation: every service in
`docker-compose.yml` publishes on `127.0.0.1` only. Do not rebind these to
`0.0.0.0` on a shared or untrusted network, because none of the six services
carry authentication.

## Controls

Prompt injection reaching the filesystem is the main risk this design has to
answer for, and it is addressed in three independent layers:

1. `src/agent/tools/logs_tool.py` resolves the service name against an explicit
   allowlist in `src/agent/tools/validation.py`. An allowlist removes the path
   traversal class rather than filtering one encoding of it. A `realpath`
   containment check sits behind the allowlist as defence in depth.
2. `src/agent/graph.py` passes webhook content as a delimited
   `<untrusted_alert_data>` block in a human message, never interpolated into the
   system prompt. The system prompt states that the block is data and must not be
   followed as instructions. Delimiter tags appearing inside alert content are
   defanged so content cannot close the block and escape into instruction
   context.
3. Every tool argument is validated at the tool boundary rather than trusting
   what the model produced. This covers `service`, `pattern`, `window_minutes`,
   `promql`, `lookback_minutes`, `query` and `message`.

`tests/test_tool_input_validation.py` and `tests/test_prompt_isolation.py` cover
these controls, including traversal attempts that must be rejected.

## Supported Python versions

This project requires **Python >= 3.10, < 3.13**.

- `fastembed==0.2.7` declares `>=3.8.0, <3.13`, so Python 3.13 cannot resolve
  this dependency set at all.
- `python-dotenv==1.2.2` declares `>=3.10`, which sets the floor.

The Docker image is built on `python:3.11-slim` and is the supported way to run
the project. Installing on Python 3.13 fails at dependency resolution, which also
prevents tools such as `pip-audit` from running against `requirements.txt` on a
3.13 host.

## Known vulnerable dependencies and reachability

Some pinned dependencies carry published advisories whose fixes are only
available across the LangChain 0.2 to 0.3 boundary. Crossing that boundary is a
breaking change for this codebase, so those pins are retained deliberately. Each
retained advisory is recorded here with the reason it is not reachable in this
application.

Pinned versions as of this document:

| Package | Pinned |
|---|---|
| `langchain-core` | 0.2.43 |
| `langchain` | 0.2.6 |
| `langgraph` | 0.1.19 |
| `python-dotenv` | 1.2.2 |

### Closed by upgrade

| CVE | Severity | Package | Resolution |
|---|---|---|---|
| CVE-2024-10940 | Moderate | `langchain-core` | Arbitrary file read from the host filesystem. Closed by moving 0.2.26 to 0.2.43, which stays inside the 0.2 line. |
| CVE-2026-28684 | Moderate | `python-dotenv` | Symlink following in `set_key` allows arbitrary file overwrite. Closed by moving 1.0.1 to 1.2.2. The project only ever calls `load_dotenv`, so it was not reachable regardless. |

### Retained, with reachability analysis

| CVE | Severity | Package | Fixed in | Why it is not reachable here |
|---|---|---|---|---|
| CVE-2025-68664 | Critical | `langchain-core` | 0.3.81 | Serialization injection enabling secret extraction through the `dumps` and `loads` APIs. This project never calls LangChain serialization: there are no `load`, `loads`, `dumpd` or `dumps` calls anywhere in `src/`. Agent state is held in memory for the duration of one request and is persisted only as plain text and JSON through `sqlite3`. |
| CVE-2026-44843 | High | `langchain-core` | 0.3.85 | Unsafe deserialization of attacker-controlled objects through an overly broad `load()` allowlist. Same reasoning: `load()` is never called. |
| CVE-2026-34070 | High | `langchain-core` | 1.2.22 | Path traversal in the legacy `load_prompt` functions. `load_prompt` is never called. Prompts are module-level string constants in `src/agent/graph.py`. |
| CVE-2025-65106 | High | `langchain-core` | 0.3.80 | Template injection via attribute access in prompt templates. This project does not use `PromptTemplate` or `ChatPromptTemplate`. The system prompt is a plain constant and the alert block is rendered with `str.format` on a fixed template whose only substitutions are the three alert fields. |
| CVE-2026-40087 | Moderate | `langchain-core` | 0.3.84 | Incomplete f-string validation in prompt templates. Not reachable for the same reason: no LangChain prompt template objects are constructed. |
| CVE-2026-26013 | Low | `langchain-core` | 1.2.11 | SSRF via `image_url` token counting in `ChatOpenAI.get_num_tokens_from_messages`. This project uses `ChatGroq`, never `ChatOpenAI`, and sends no image content. |
| CVE-2026-45134 | High | `langchain` | 0.3.30 | The LangSmith SDK deserializes untrusted manifests when pulling a public prompt. This project performs no prompt-hub pulls: there is no `hub.pull` usage and LangSmith tracing is not enabled. Tracing goes to Langfuse through a callback handler. |
| CVE-2026-55443 | Moderate | `langchain` | 0.3.30 | Path traversal and sandbox escape in the file-search middleware and loaders. Neither the middleware nor any LangChain document loader is used. |
| CVE-2026-48776 | High | `langgraph` | 0.3.15 | Unsafe msgpack deserialization when loading checkpoints. The graph is compiled with `builder.compile()` and no checkpointer, so no checkpoint is ever written or loaded. Verify with `grep -rn "checkpointer" src/`, which returns nothing. |

### Re-checking this analysis

```
python3 - <<'PY'
import json, urllib.request
for name, ver in [("langchain-core","0.2.43"), ("langchain","0.2.6"),
                  ("langgraph","0.1.19"), ("python-dotenv","1.2.2")]:
    body = json.dumps({"package": {"name": name, "ecosystem": "PyPI"},
                       "version": ver}).encode()
    req = urllib.request.Request("https://api.osv.dev/v1/query", data=body,
                                 headers={"Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    print(name, ver, [v.get("id") for v in data.get("vulns", [])])
PY
```

If any of the reachability assumptions above stop holding, for example if a
checkpointer is added to the graph or a LangChain prompt template is introduced,
the corresponding advisory becomes live and the dependency must be upgraded
across the 0.3 boundary at that point.
