# CATS Thesis — Static Audit Report v6 FINAL

| Field | Value |
|--------|--------|
| **Repo** | `CATS_Thesis/` |
| **Plan** | `THESIS_MASTER_PLAN_v5_FINAL.md` (v5.0 FINAL) |
| **Method** | Static read-only: source, compose, tests, benchmark/eval scripts |
| **Runtime** | NOT EXECUTED (docker/smoke/benchmark) |
| **Verdict** | **NO-GO** for official **24-run benchmark** and thesis evaluation pipeline |
| **Core implementation** | ~**82–88%** vs plan (Tier-1/2 + compose + OPA skeleton present; harness + metrics/policy gaps remain) |
| **Checklist** | Static checklist complete; runtime GO requires §8 Smoke on Ubuntu |

**Supersedes:** `cats_static_audit_report_v5_FINAL.md`  
**Incorporates:** §8 reference fix, HIGH-12 GO criteria inclusion, refined OPA timeout math (≤5–10ms), fully restored §10 grep commands, and improved MED-02 dataset fallback logic.

---

## §1 Executive summary

The system is **close enough** for a CATS routing demo (two-tier + OPA on Docker) but **not ready** for the plan’s **24-experiment matrix** or defensible thesis evaluation numbers.

### Five NO-GO reasons (unchanged)

1. `benchmark/run_all.py` — **5 ad-hoc scenarios**, not **3×2×4 = 24**.
2. `benchmark/run_experiment.py` — missing **10-step isolation** (plan §5.5).
3. Toxiproxy proxies — **not** auto-created on `docker compose up` (manual `network/init_proxies.py`).
4. **OPA Rule 5 dead** — code sends `STATE_DEGRADED`, Rego checks `"DEGRADED"`.
5. **Unit test CATS weights wrong** (0.40/0.30/0.20/0.10 vs code 0.30/0.30/0.25/0.15).

### Additional HIGH gaps

OPA hot-path (new client per call, fail-open, 2× calls), RULE 3 near-dead, queue semantics ≠ plan, Prometheus gateway scrape broken, eval scripts below plan scale, ShareGPT dataset missing.

---

## §2 Scope & methodology

**Read:** `docker-compose.yml`, `orchestrator/*`, `gateway/*`, `safety/policies/routing.rego`, `benchmark/*`, `evaluation/*`, `tests/*`, `telemetry/prometheus.yml`, `.env`, `.gitignore`, `THESIS_MASTER_PLAN_v5_FINAL.md`.

**Not run:** `docker compose up`, Locust 24-run, measured P99, `opa test`, host GPU validation.

**Re-check:** Each finding has **Evidence** (file + line/pattern) or **Verify command** in §10.

---

## §3 Alignment matrix (plan vs code)

| Area | Plan | Code | Status |
|------|------|------|--------|
| Compose (cloud/edge/toxi/opa/orch/gw/prom/grafana) | ✓ | ✓ | **PASS** |
| Tier-1 `STATE_*` + routing templates | ✓ | ✓ `strategic_agent.py` | **PASS** |
| Tier-2 CATS × template | ✓ | ✓ `orchestrator/main.py` | **PASS** |
| OPA 5 rules | ✓ | Rule 5 **dead** | **FAIL** |
| 8 metrics incl. `mem_pressure` | ✓ §3.3 | Not implemented | **FAIL** |
| Queue from `/api/ps` | ✓ | Poll only, no parse | **FAIL** |
| 24 benchmark matrix | ✓ §5.1 | 5 scenarios | **FAIL** |
| Experiment isolation §5.5 | ✓ | Missing | **FAIL** |
| ShareGPT 500 prompts | ✓ | 20 synthetic prompts | **FAIL** |
| Tier-1 eval 100 snapshots | ✓ | 5 cases | **FAIL** |
| ROUGE 100 samples | ✓ | 3 prompts | **FAIL** |
| Routing P99 < 10ms | ✓ Phase 3 | OPA HTTP 2×, timeout 1s | **FAIL** (unmeasured) |
| Gateway `/metrics` for Prometheus | implied | No route | **FAIL** |

---

## §4 BLOCKERS (BLK)

### BLK-01 — Benchmark matrix ≠ 24 experiments

- **Plan:** §5.1 — `3 network × 2 load × 4 strategies = 24`
- **Evidence:** `benchmark/run_all.py` (L4-L9) — `SCENARIOS` has 5 entries; no nested profile/load/strategy loops.
- **Fix:** Rewrite `run_all.py` + `run_experiment.py` with full matrix; env `BENCHMARK_STRATEGY`; use `network/profiles/good|medium|bad`.
- **Acceptance:** Exactly 24 runs; each run has CSV + metadata for all three dimensions.

### BLK-02 — Experiment isolation procedure missing

- **Plan:** §5.5 steps 1–10 (drain queue, reset toxics, restart gateway, warmup, etc.)
- **Evidence:** `benchmark/run_experiment.py` — toxics + Locust only.
- **Fix:** Implement all 10 steps in `run_experiment.py` or `benchmark/isolation.py`.
- **Acceptance:** Logged steps; queues drained before next run.

### BLK-03 — Unit tests assert wrong CATS weights

- **Evidence:** `tests/unit/test_cats_scoring.py` (L6-L49) expects `0.40/0.30/0.20/0.10`; `orchestrator/config.py` and `tactical_agent.py` use `0.30/0.30/0.25/0.15`.
- **Fix:** Update all 30 parametrized expected values.
- **Verify:** `pytest tests/unit/test_cats_scoring.py -q`

### BLK-04 — Toxiproxy proxies not created on compose up

- **Evidence:** `docker-compose.yml` (L70-L84) — `toxiproxy` service only; no init service. `network/init_proxies.py` is manual.
- **Fix:** Add one-shot `toxiproxy-init` service or entrypoint. **Crucial:** If running inside the Docker network, the script MUST target `http://toxiproxy:8474`, NOT `localhost`. Also correct the path to `toxiproxy_init.json`.
- **Verify:** After `docker compose up`, `curl http://localhost:8474/proxies` lists `cloud-proxy` and `edge-proxy`.

### BLK-05 — Dataset ≠ ShareGPT per plan

- **Plan:** `benchmark/prompts/sharegpt_500.json`
- **Evidence:** `benchmark/prepare_dataset.py` (L5-L26) — 20 hardcoded prompts → `data/prompts.json`.
- **Fix:** HF ShareGPT pipeline + truncation; point Locust to final path.
- **Acceptance:** ≥500 samples; tag mix 70% default / 20% fast_ok / 10% high_quality.

---

## §5 HIGH priority

### HIGH-01 — OPA Rule 5 never fires (state string mismatch)

- **Evidence:**
  - `orchestrator/strategic_agent.py` — states like `STATE_DEGRADED`
  - `safety/policies/routing.rego` L54–58: `input.site_state == "DEGRADED"`
  - `orchestrator/tactical_agent.py` L62 — passes full `current_state` as `site_state`
- **Fix (recommended):** Rego: `input.site_state == "STATE_DEGRADED"` **or** normalize before OPA (strip `STATE_` prefix).
- **Plan drift:** Plan §3.7 L326 says `"DEGRADED"`; runtime uses `STATE_*` — pick **one convention** for thesis, Rego, and tests.

### HIGH-02 — OPA on hot path; P99 < 10ms not achievable as documented

- **Evidence:**
  - `orchestrator/main.py` L119–126 — up to **2×** `check_opa_safety`
  - `orchestrator/tactical_agent.py` L42-75 — **new** `httpx.AsyncClient` per call, `timeout=1.0s`, and synchronous RLock `get_all()` contention.
  - Plan Phase 3 — “P99 < 10ms”, “no network call in hot path” — **contradicts** OPA HTTP
- **Fix bundle:**
  1. Shared `AsyncClient`; **timeout ≤5–10ms** if keeping strict P99 <10ms claim.
  2. Metrics: `cats_opa_latency_ms`, `cats_routing_compute_ms` on orchestrator `/metrics`
  3. Optional: short-TTL policy cache to avoid event loop blocking.
- **Acceptance (choose one; document in thesis):**
  - **A:** P99 end-to-end `POST /route` < 10ms (requires strict 5ms OPA timeout).
  - **B:** P99 excluding OPA + report OPA p99 separately (allows 10-20ms OPA timeout).
  - **C:** Relax plan claim.

### HIGH-03 — OPA fail-open on error

- **Evidence:** `tactical_agent.py` L73–75 — `except` → `return True, []` silently.
- **Risk:** Safety bypass when OPA is down goes unrecorded.
- **Fix:** Add `opa_status: "enforced" | "bypassed"` to the routing decision. Collect and flag bypass count in benchmark CSV.
- **Thesis:** Document fail-safe behavior.

### HIGH-04 — `@async_retry` ineffective on OPA

- **Evidence:** Inner `try/except` swallows exceptions; retry never triggers.
- **Fix:** Re-raise retryable errors or remove decorator.

### HIGH-05 — RULE 3 (SLA) effectively dead

- **Evidence:** `predicted_latency_ms` = Toxiproxy `*_latency_ms` (typically < 500); `sla_target_ms=500` → rare `SLA_VIOLATION`.
- **Fix:** Use TTFT estimate, queue penalty, or separate `predicted_e2e_ms`.
- **Acceptance:** Inject 600ms latency, SLA 500 → `SLA_VIOLATION`.

### HIGH-06 — `mem_pressure` metric (severity conditional)

| Thesis decision | Severity | Action |
|-----------------|----------|--------|
| Keep **8 metrics** in Ch. 3/5 | **HIGH** | Implement `/proc/meminfo` in `compute_reader.py` + Prometheus |
| Remove from thesis/scoring | **MEDIUM** | Update plan + Limitations; rename to **MED-DRIFT-01** |

- **Evidence:** Plan §3.3 L218 only; not in `metrics_cache` defaults.

### HIGH-07 — Queue depth ≠ Ollama queue

- **Evidence:**
  - Gateway `in_flight` → `POST /metrics/update` (`gateway/main.py`)
  - `compute_reader.fetch_queue_depth` (L69-L85) — GET `/api/ps` without parsing
  - Plan — queue from `/api/ps`
- **Fix:** **DO NOT attempt to parse `/api/ps`** (Ollama doesn't expose queue depth there). Rename thesis metric to `gateway_inflight` and document as proxy, OR implement an application-level queue counter in the gateway.
- **Acceptance:** Under load, metric behavior documented and consistent with OPA RULE 1.

### HIGH-08 — GPU util from orchestrator container

- **Evidence:** `compute_reader.py` (L40-L56) — `nvidia-smi` inside orchestrator (usually no GPU → 0).
- **Fix:** Exporter on `cloud-node`, remote poll, or thesis limitation “GPU metric N/A in prototype”.
- **Impact:** OPA RULE 2 cloud GPU; CATS compute term for cloud.

### HIGH-09 — Prometheus scrapes missing gateway `/metrics`

- **Evidence:** `telemetry/prometheus.yml` (L6-L11) → `gateway:8000/metrics`; `gateway/main.py` has no `/metrics`.
- **Fix:** Add gateway `/metrics` or remove scrape job.

### HIGH-10 — `evaluate_tier1.py` threshold drift vs production

- **Evidence:** Eval prompt uses queue>20, cpu>80, latency>100, burst 3×; `config.py` uses 35, 85, 150, 1.5×. Only **5** test cases vs plan **100** snapshots.
- **Fix:** Import `settings`; expand to 100 cases; confusion matrix output.

### HIGH-11 — `rouge_eval.py` not plan-compliant

- **Evidence:** 3 prompts; plan requires 100 via `/quality-sample` after 24 runs.
- **Fix:** Batch script + dataset subset.

### HIGH-12 — `test_opa_rules.py` not real OPA tests

- **Evidence:** String presence checks only; no `opa eval` / `opa test`.
- **Fix:** Rego test files + CI `opa test` or dockerized `opa eval` with fixtures.

---

## §6 MEDIUM

| ID | Issue | Evidence | Fix |
|----|--------|----------|-----|
| MED-01 | `evaluate_tier1.py` uses `localhost:11435` | `evaluation/evaluate_tier1.py` L68 | Document host-only run; or env URL |
| MED-02 | Locust reads `data/prompts.json` | `benchmark/locustfile.py` L8 | **Fix: Read `benchmark/prompts/sharegpt_500.json`, fallback to `prepare_dataset.py` if missing** |
| MED-03 | `run_experiment` toxics ≠ good/medium/bad profiles | `run_experiment.py` | Use `network/profiles/*.py` |
| MED-04 | Plan snippet `EDGE_METRICS_URL` :11435 vs `.env` :11434 | plan L204–205 vs `.env` L7 | Inside Docker **11434 is correct**; fix plan host-map note |
| MED-05 | CPU isolation: `limits.cpus` not cpuset | `docker-compose.yml` (L37-L38) | **Fix: Use `cpuset: "0-5"`** instead of `limits.cpus` to match plan |
| MED-06 | CI may skip real OPA | `test_opa_rules.py` | OPA service in CI |
| MED-07 | `run_all` does not set `BENCHMARK_STRATEGY` per run | `run_all.py` | Env per experiment |
| MED-08 | Analysis scripts not wired | `analysis/*.py` | Phase 9 Makefile targets |
| MED-09 | `_push_metrics` overhead per request | `gateway/main.py` (L194-L241) | Fix: Batch metric pushes or reduce to 1 per request to reduce load |

---

## §7 LOW

### LOW-01 — `.gitignore` missing artifacts

Add: `results/`, generated `data/prompts.json` (if not committed), `.pytest_cache/`, `htmlcov/`.

### LOW-02 — Agent tooling path (verify on disk)

- Use **`.agent/`** if present.
- Add `.agent/` to `.gitignore` if tooling should not be committed.

### LOW-03 — `test_routing_decision.py` Rule 4 test skipped (`pass` at L55).

### LOW-04 — RULE 4 in Python (`FORCE_CLOUD_FALLBACK`), not Rego — OK if documented in thesis.

---

## §8 Smoke test suite

**Prerequisite:** Ubuntu 22.04, NVIDIA driver, `docker compose up`, run `cd network && python init_proxies.py` until BLK-04 is fixed.

| ID | Test | Procedure | Expected |
|----|------|-----------|----------|
| SMOKE-01 | Orchestrator health | `curl -sf http://localhost:8080/health` | `{"status":"ok"}` |
| SMOKE-02 | Ready + metrics | `curl -sf http://localhost:8080/health/ready` | `metrics_populated: true` (after ~10s) |
| SMOKE-03 | Toxiproxy proxies | `curl -sf http://localhost:8474/proxies` | `cloud-proxy`, `edge-proxy` |
| SMOKE-04 | OPA health | `curl -sf http://localhost:8181/health` | 200 |
| SMOKE-05 | Gateway chat | `curl -sf -X POST http://localhost:8000/v1/chat -H "X-API-Key: thesis-demo-key" -H "Content-Type: application/json" -d '{"prompt":"hi","request_tag":"default"}'` | 200, route in body |
| SMOKE-06 | Route API | `curl -sf -X POST http://localhost:8080/route -H "Content-Type: application/json" -d '{"prompt":"hi","request_tag":"default"}'` | `decision`, `decision_time_ms` |
| SMOKE-07 | RULE 1 via OPA | §8.1 curl, `queue_depth: 55` | `QUEUE_OVERLOAD` |
| SMOKE-08 | RULE 3 via OPA | `predicted_latency_ms: 600`, `sla_target_ms: 500` | `SLA_VIOLATION` |
| SMOKE-09a | RULE 5 policy | §8.1 curl, `high_quality` + `STATE_DEGRADED` (after HIGH-01) | `EDGE_DEGRADED_HQ`, `allow: false` |
| SMOKE-09b | RULE 5 via `/route` | **BLOCKED** — no HTTP API to set `shared_state` | Use pytest `shared_state.update()` or optional `POST /debug/tier1-state` |
| SMOKE-10 | Unit tests | `pytest tests/unit -q` | Pass after BLK-03 |
| SMOKE-11 | Prometheus | `curl -sf http://localhost:9090/-/healthy` + query `cats_network_latency_ms` | Orchestrator series present |
| SMOKE-12 | Routing latency | 1000× `POST /route`, compute P99 of `decision_time_ms` | Compare to §HIGH-02 acceptance choice |

*(§8.1 OPA curl template omitted for brevity, unchanged from v4).*

---

## §9 Implementation phases

### Phase 1a — Stack runnable (E2E first)

| Order | ID | Task |
|-------|-----|------|
| 1 | BLK-04 | Toxiproxy auto-init on compose up |
| 2 | HIGH-01 | Fix OPA Rule 5 state string |
| 3 | HIGH-02–04 | OPA client reuse, timeout, metrics, fail mode |
| 4 | HIGH-07–09 | Queue semantics, GPU metric, Prometheus |
| 5 | HIGH-05 | RULE 3 signal (recommended) |

### Phase 1b — CI trustworthy

| Order | ID | Task |
|-------|-----|------|
| 1 | BLK-03 | Fix `test_cats_scoring.py` weights |
| 2 | HIGH-12 | Real OPA tests |
| 3 | MED-06 | CI OPA service |
| 4 | — | `pytest tests/unit` green |

### Phase 2 — Benchmark infrastructure

BLK-01, BLK-02, BLK-05, MED-03, MED-05, MED-07, MED-09

### Phase 3 — Evaluation & thesis writing

HIGH-10, HIGH-11, analysis plots, full 24-run, ROUGE/Tier-1 at plan scale

### GO criteria (official 24-run benchmark)

- [ ] SMOKE-01–12 pass on Ubuntu host
- [ ] BLK-01–05 closed
- [ ] HIGH-01–12 closed or accepted with documented thesis limitation
- [ ] One dry-run (PROPOSED, GOOD, LOW) produces valid CSV
- [ ] 24/24 experiments complete with isolation logs
- [ ] Chapter 5 numbers derived from those artifacts only

---

## §10 Re-check appendix (grep / commands)

```bash
# Rule 5 mismatch
rg 'site_state.*DEGRADED' safety/policies routing.rego orchestrator/

# Wrong test weights
rg '0\.40 \*' tests/unit/test_cats_scoring.py

# 24 vs 5 runs
rg 'SCENARIOS' benchmark/run_all.py

# Gateway /metrics missing
rg '@app\.(get|post).*metrics' gateway/main.py

# mem_pressure only in plan
rg 'mem_pressure' .

# shared_state HTTP endpoint (should be empty)
rg 'shared_state\.update|/debug|tier1.state' orchestrator/main.py
```

---

## §11 Sign-off

| Gate | Status |
|------|--------|
| Static audit v6 document | **COMPLETE** |
| Code ready for official 24-run | **NO** |
| Thesis evaluation claims | **NO-GO** until Phase 2–3 + runtime smoke |
| Runtime smoke (§8) | **PENDING** — run on thesis machine |
