# SafeBench patches for AAAI-IRT

This directory carries the minimal local patches we apply to SafeBench so that
its default eval logger carries enough information for our measurement model
(`analysis/b4-pipeline/`).

## Patch 1: `route_scenario.py` — background vehicle trajectories in records.pkl

Resolves the residual risk noted in `research/decisions.html` D-08 ("background
trajectory hook may be required"). SafeBench already tracks every
`vehicle.*` actor inside `gym_carla/envs/carla_env.py` but the per-step record
written to `records.pkl` only carries ego state. Our patch adds a single
`bg_trajectories` field to the step dict via a new helper
`_aaai_collect_bg_trajectories` on `RouteScenario`.

Files:
- `route_scenario_original.py` — verbatim copy from `safebench/safebench/scenario/scenario_definition/route_scenario.py` inside the `safebench/safebench:latest` docker image (2026-06-03 pull).
- `route_scenario_patched.py` — same file with one new method and a single new key in `get_running_status`.

How to apply (idempotent — overwrites the file inside the container):

```bash
docker cp patches/safebench/route_scenario_patched.py \
    <container>:/home/safebench/SafeBench/safebench/scenario/scenario_definition/route_scenario.py
```

After applying, the `bg_trajectories` key shows up in every step dict inside
`records.pkl`. `analysis/b4-pipeline/sb_to_response.py` reads it as
`bg_traj` so `analysis/b4-pipeline/rss_labeler.py` can run.

We deliberately keep the patch tiny (one helper + one key) so the diff against
upstream SafeBench is easy to audit and re-apply when SafeBench updates.
