# CATS Next Steps Agent Brief

## Purpose

This file is the operating brief for the next AI/code agent working on CATS.

The project should move in a combined direction:

1. Build a practical, working cloud-edge LLM inference routing prototype.
2. Preserve enough academic rigor to defend the thesis claims with controlled benchmark evidence.

Do not treat every item in `THESIS_MASTER_PLAN_v5_FINAL.md` as equally important. The implementation priority is:

1. Runtime correctness.
2. Metric correctness.
3. Benchmark reproducibility.
4. Thesis evidence.
5. Optional polish.

Primary audit baseline:

- `cats_static_audit_report_v6_FINAL.md`
- `THESIS_MASTER_PLAN_v5_FINAL.md`

Before changing code, re-open the relevant source files and verify the finding still exists. Do not blindly patch from the report.

---

## Current Verdict

The project is not ready for the official 24-run benchmark campaign.

It is close to a working research-grade prototype, but several core runtime and measurement issues must be fixed before benchmark numbers can be trusted.

Current rough state:

| Area | Status |
|---|---|
| Core architecture | Mostly present |
| End-to-end runtime wiring | Not reliable yet |
| Metrics semantics | Partially incorrect |
| OPA safety gate | Partially broken |
| Benchmark automation | Not ready |
| Thesis evaluation evidence | Not ready |
| Production readiness | Not production; research prototype only |

---

## Severity Model For Future Work

Use this classification instead of treating all audit findings the same.

### Runtime-Critical

Must be fixed for the system to run correctly or route safely.

Examples:

- Toxiproxy proxy creation.
- OPA Rule 5 state mismatch.
- OPA fail-open visibility.
- `predicted_latency_ms` semantics.
- queue/in-flight metric semantics.
- Prometheus scrape mismatch if it affects validation.

### Benchmark-Critical

Must be fixed before collecting official thesis numbers.

Examples:

- 24-run matrix.
- experiment isolation.
- model warmup.
- profile verification.
- benchmark CSV schema.
- reproducible dataset.

### Thesis-Supporting

Needed only if the thesis keeps the corresponding claim.

Examples:

- Tier-1 classifier 100-snapshot evaluation.
- ROUGE-L paired quality evaluation.
- `mem_pressure` metric if the thesis claims 8 metrics.
- analysis plots.

### Optional / Defer

Useful cleanup but not a blocker.

Examples:

- Makefile convenience targets.
- extra dashboards.
- `.agent/` cleanup.
- non-critical analysis scripts.

---

## Phase 1: Make The Runtime Correct

Goal: the stack should run end-to-end on Linux and the route decision should not rely on broken policy or misleading telemetry.

### 1.1 Auto-create Toxiproxy proxies

Problem:

- `docker-compose.yml` starts Toxiproxy, but it does not create `cloud-proxy` and `edge-proxy`.
- `network/init_proxies.py` is manual.

Required outcome:

- `docker compose up` must result in Toxiproxy having both proxies.

Implementation options:

1. Add a one-shot `toxiproxy-init` service.
2. Or wire proxy creation into orchestrator startup.

Important details:

- If the init script runs inside Docker network, use `http://toxiproxy:8474`.
- If the script runs from the host, use `http://localhost:8474`.
- Fix path handling in `network/init_proxies.py`; do not rely on current working directory. Use `Path(__file__).with_name("toxiproxy_init.json")`.

Acceptance:

```bash
docker compose up -d
curl -sf http://localhost:8474/proxies
```

The response must include `cloud-proxy` and `edge-proxy`.

### 1.2 Fix OPA Rule 5 state mismatch

Problem:

- Code sends states like `STATE_DEGRADED`.
- Rego checks `DEGRADED`.
- Rule 5 never fires.

Recommended fix:

- Standardize on `STATE_*` everywhere.
- Change `safety/policies/routing.rego` to check `STATE_DEGRADED`.
- Update tests and thesis wording to match.

Acceptance:

- Direct OPA input with `site=edge`, `request_tag=high_quality`, `site_state=STATE_DEGRADED` returns `allow=false` and includes `EDGE_DEGRADED_HQ`.

### 1.3 Fix OPA hot path behavior

Problem:

- `check_opa_safety()` creates a new `httpx.AsyncClient` per route decision.
- OPA HTTP call is in the request hot path.
- timeout is currently too high for a strict `<10ms` route decision claim.
- fail-open returns `True, []`, making bypass indistinguishable from a clean allow.

Required outcome:

- Use a shared `AsyncClient`.
- Remove ineffective `@async_retry` or make retry semantics explicit outside the hot path.
- Add `opa_status`: `enforced` or `bypassed`.
- Record OPA latency as a metric.

Decision required:

- If the thesis keeps strict end-to-end `POST /route P99 < 10ms`, use very low timeout and measure it on Linux.
- If OPA remains a network call, consider changing the thesis claim to separate routing compute latency from OPA latency.

Acceptance:

- Route response includes OPA status.
- Benchmark CSV can count OPA bypasses.
- 1000 route requests report P99 based on the selected acceptance mode.

### 1.4 Fix `predicted_latency_ms`

Problem:

- Tactical Agent currently sends Toxiproxy network latency as `predicted_latency_ms`.
- OPA Rule 3 compares it to SLA.
- This makes SLA policy mostly ineffective because inference time is ignored.

Recommended fix:

Use a clear `predicted_e2e_ms` value:

```text
predicted_e2e_ms = network_latency_ms + site_ttft_ms_avg + queue_penalty_ms
```

If the system cannot estimate this reliably yet, rename or document the field honestly and weaken the SLA claim.

Acceptance:

- Injecting predicted latency above SLA produces `SLA_VIOLATION`.
- Normal profiles do not trigger false positives.

### 1.5 Fix queue metric semantics

Problem:

- Plan says queue depth comes from Ollama `/api/ps`.
- Ollama `/api/ps` does not expose real queue depth.
- Current value is gateway `in_flight`, not Ollama internal queue.

Do not attempt to fake parsing `/api/ps` as queue depth.

Choose one:

1. Rename the metric to `gateway_inflight` and document it as a proxy metric.
2. Implement application-level queue accounting in gateway/orchestrator.

Recommended practical path:

- Use `gateway_inflight` for prototype routing.
- Update thesis text to say this is a proxy for inference pressure, not internal Ollama queue.

Acceptance:

- Metric name and thesis claim match.
- OPA Rule 1 and CATS score use the same documented semantic.

### 1.6 Fix compute signals or document limitations

Known issues:

- `nvidia-smi` is called from orchestrator container, which likely does not have GPU access.
- `/proc/stat` from orchestrator does not necessarily represent edge-node CPU.

Practical options:

1. Add lightweight exporters/sidecars for cloud GPU and edge CPU.
2. Poll Docker Stats API.
3. Document compute metrics as limited prototype signals and reduce their thesis claim.

Acceptance:

- Under cloud inference, `cloud_gpu_util` should be non-zero if claim is kept.
- Under edge load, `edge_cpu_util` should reflect edge-node pressure if claim is kept.

### 1.7 Fix Prometheus scrape mismatch

Problem:

- Prometheus scrapes `gateway:8000/metrics`.
- Gateway currently does not expose `/metrics`.

Choose one:

1. Add gateway `/metrics`.
2. Remove the gateway scrape job and keep orchestrator `/metrics` as the single source.

Acceptance:

- Prometheus has no failing scrape jobs during benchmark.
- Grafana panels only query emitted metrics.

---

## Phase 2: Make Tests And CI Trustworthy

Goal: test failures should point to real regressions, not stale expected values.

### 2.1 Fix CATS scoring tests

Problem:

- `tests/unit/test_cats_scoring.py` uses old weights and quality scores.

Expected current values:

```text
W_LATENCY = 0.30
W_QUEUE = 0.30
W_COMPUTE = 0.25
W_QUALITY = 0.15
QUALITY_CLOUD = 1.0
QUALITY_EDGE = 0.6
```

Acceptance:

```bash
pytest tests/unit/test_cats_scoring.py -q
```

passes on Linux.

### 2.2 Add real OPA tests

Problem:

- `test_opa_rules.py` is mostly string presence checking.

Required outcome:

- Add Rego fixtures or dockerized `opa eval`.
- Test all rule scenarios:
  - queue overload.
  - cloud GPU overload.
  - edge CPU overload.
  - SLA violation.
  - high-quality edge degraded rejection.

Acceptance:

- CI fails if Rego rule semantics break.

### 2.3 Fix strategic fallback tests

Problem:

- Some tests use old thresholds.

Required outcome:

- Use current thresholds from config or import settings.

Acceptance:

```bash
pytest tests/unit/test_strategic_agent.py -q
```

passes on Linux.

---

## Phase 3: Make One Benchmark Run Trustworthy

Goal: one run should be reproducible before expanding to 24 runs.

### 3.1 Implement experiment isolation

Create a clear function or module, for example:

```text
benchmark/isolation.py
```

Minimum required steps:

1. Stop load generator.
2. Wait for in-flight requests to drain.
3. Reset Toxiproxy toxics.
4. Apply target network profile.
5. Verify profile values through Toxiproxy API.
6. Set `BENCHMARK_STRATEGY`.
7. Restart or reload gateway.
8. Warm up cloud and edge models.
9. Wait stabilization window.
10. Start Locust and collect metadata.

Acceptance:

- One dry run `PROPOSED + GOOD + LOW` produces valid CSV and metadata.

### 3.2 Fix dataset path and generation

For official thesis benchmark:

- Use `benchmark/prompts/sharegpt_500.json`, or a documented practical workload dataset.
- Dataset must be reproducible.
- Keep tag mix:
  - 70% `default`
  - 20% `fast_ok`
  - 10% `high_quality`

Development fallback is allowed only for smoke testing. Do not use fallback prompts for official numbers.

Acceptance:

- Locust reads the official benchmark prompt file.
- Missing dataset should fail official benchmark mode, not silently fall back to `"Hello"`.

### 3.3 Define benchmark CSV schema

Each run should record:

- timestamp.
- strategy.
- profile.
- load level.
- prompt id.
- request tag.
- route decision.
- model.
- latency/e2e ms.
- TTFT ms if available.
- OPA status.
- OPA violations.
- SLA violation flag.
- error status.

Acceptance:

- Analysis scripts can consume the CSV without guessing column names.

---

## Phase 4: Expand To The 24-Run Matrix

Goal: collect thesis-grade comparative data.

Required matrix:

```text
3 network profiles x 2 load levels x 4 strategies = 24 runs
```

Profiles:

- GOOD.
- MEDIUM.
- BAD.

Loads:

- LOW.
- HIGH.

Strategies:

- PROPOSED.
- BASELINE-1.
- BASELINE-2.
- BASELINE-3.

Acceptance:

- `run_all.py` produces exactly 24 run artifacts.
- Each artifact has metadata identifying profile, load, and strategy.
- Isolation logs exist for every run.
- Failed runs are marked and not silently included in analysis.

---

## Phase 5: Add Thesis Evidence Without Overbuilding

Goal: support thesis claims without making academic extras block the practical system unnecessarily.

### 5.1 Tier-1 classifier evaluation

Keep this if the thesis claims LLM-as-classifier or agentic strategic reasoning.

Minimum:

- 100 labeled snapshots.
- balanced enough across 5 states.
- confusion matrix.
- accuracy summary.

If practical direction becomes rule-based first:

- Present LLM classifier as extensibility experiment, not production controller.

### 5.2 ROUGE-L paired evaluation

Keep this only if the thesis claims quality-latency trade-off.

Minimum:

- 100 paired prompts.
- cloud response as reference.
- edge response as hypothesis.
- record route/context.

If quality is not a main claim:

- Move ROUGE-L to appendix or reduce emphasis.

### 5.3 `mem_pressure`

Decision required:

1. Implement it and keep the "8 metrics" claim.
2. Remove it from the main claim and document as future work / limitation.

Do not leave the thesis saying the system uses a metric that code does not collect.

---

## Phase 6: Practical Smoke Tests Before Official Benchmark

Run on Ubuntu/Linux host only.

Required smoke tests:

1. `docker compose up` brings all services healthy.
2. Toxiproxy proxies exist.
3. Gateway `/v1/chat` succeeds.
4. Orchestrator `/route` succeeds.
5. GOOD -> MEDIUM -> BAD profile changes appear in MetricsCache.
6. OPA Rule 1 rejects queue overload.
7. OPA Rule 3 rejects SLA violation.
8. OPA Rule 5 rejects high-quality edge degraded.
9. Unit tests pass.
10. Prometheus has no failing critical scrape.
11. One full dry run creates valid CSV.
12. Routing latency measurement is reported according to the chosen P99 definition.

Do not start the official 24-run benchmark until these pass or are explicitly documented as limitations.

---

## Recommended Claim For Thesis

Use a practical, defensible claim:

> CATS is a research-grade prototype for cloud-edge LLM inference routing. It combines network-emulated telemetry, gateway load signals, compute signals, and OPA policy checks to reduce latency and SLA violations compared with static routing baselines under controlled benchmark conditions.

Avoid overclaiming:

- Do not claim production-grade reliability.
- Do not claim exact Ollama queue depth unless implemented.
- Do not claim full compute telemetry if GPU/CPU signals are proxy or unavailable.
- Do not claim quality optimization unless ROUGE-L evaluation is completed.

---

## What The Next Agent Should Do First

Start with Phase 1a, not the 24-run benchmark.

Suggested first task order:

1. Fix Toxiproxy auto-init.
2. Fix OPA Rule 5.
3. Add OPA status and shared client.
4. Fix `predicted_latency_ms` semantics.
5. Rename/document queue metric.
6. Fix Prometheus scrape.
7. Fix scoring tests.
8. Run unit tests on Linux.
9. Run smoke test.
10. Only then implement benchmark isolation and 24-run automation.

---

## Guardrails For AI Agents

- Do not run official benchmark until smoke tests pass.
- Do not silently change thesis claims without updating the plan/report.
- Do not create new abstractions unless they remove real complexity.
- Do not treat synthetic `"Hello"` prompts as benchmark data.
- Do not hide OPA bypasses.
- Do not report metrics that are not emitted.
- Do not mark the system GO based on static audit alone.

