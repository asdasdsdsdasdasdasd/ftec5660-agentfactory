# Zoom Speaker Script (~12.5 min spoken, 15 min slot)

Spoken text is **English**. Lines in `【切屏】` are private Chinese cues — glance, do not read.

**Rubric map (say these four things, in this order):**
1. What the paper claims, and what we reproduced.
2. Setup + Edge Case A substitutions.
3. Numbers vs Table 1, with the comparability caveat.
4. Isolated, measurable modification (local Qwen subagents) and the ablation delta.

---

## 0:00–0:40  Opening

**【切屏】** 开场脸出镜，先别切幻灯。计时器启动。然后切到 `02_…Slides.html` **Slide 1 Title**。

Good evening. This is a reproducibility study of **AgentFactory**, the ACL 2026 demo paper by Zhang et al. The paper’s claim is simple: if an agent **saves successful solutions as executable Python subagents**, not as text memories, then a second, similar batch of tasks should need **less orchestrator work**.

We ran the **authors’ repository**, not a reimplementation. Meta-agent is **DeepSeek V4.1 Flash**. Subagents in our modification run on a **local Qwen 3.8 27B** on this machine.

---

## 0:40–2:10  Paper + reproduction target  *(Rubric 1)*

**【切屏】** **Slide 2 Paper**. 用鼠标指三个阶段：Install / Self-Evolve / Deploy。

AgentFactory has three phases. **Install** is Batch 1: the meta-agent solves tasks from scratch, writes Python modules, and stores a `SKILL.md` for each. **Self-evolve** is Batch 2: same family of tasks, but the meta-agent can `list`, `read`, `run`, or `modify` those saved skills. **Deploy** is exporting those scripts outside the framework — we did not re-run an external framework; we show the saved skills themselves.

The reproduction target is **Section 5, Table 1**. Metric is **meta-agent output tokens per task**, excluding LLM tokens spent *inside* subagents. Paper numbers: Claude Opus **4,324 → 2,971 (−31%)**; Sonnet **9,199 → 3,862 (−58%)**.

We ran all **15 Batch-1** questions, then Batch 2 with **Q2, Q10, Q12 scoped out** — Tencent Meeting login, HuggingFace JS leaderboard, QQ Music VIP. That leaves **12 paired tasks** for every comparison.

---

## 2:10–3:40  Setup  *(Rubric 2)*

**【切屏】** **Slide 3 Setup**. 指表格三行：Meta、Sub、Search。

**Edge Case A:** we did not have Claude Opus or Sonnet, and we did not use Serper or Jina.

| Role | Paper | Ours |
|---|---|---|
| Meta | Claude 4.6 | `deepseek-flash` |
| Search / fetch | Serper + Jina | DeepSeek Search + Fetch, same tool names |
| Browser | Logged-in Chrome | Headless Playwright Chromium |
| Subagent (control) | Same as meta | `deepseek-flash` |
| Subagent (modification) | — | Local `Qwen3.8-27B-Q4_K_M` on two RTX 5070 Ti |

Hardware is this box: Ryzen 9 9950X, 60 GiB RAM, dual 16 GB GPUs. Local server is llama.cpp / Strata on `127.0.0.1:8080`.

Because tokenizer and retrieval backend changed, **absolute tokens are not comparable to Table 1**. All of *our* deltas — Batch 1 vs Batch 2, homogeneous vs heterogeneous — use the **same prompts, same task files, same metric**.

---

## 3:40–6:10  Results vs paper  *(Rubric 3)*

**【切屏】** **Slide 4 Fig 1**. 先指 Paper 两根绿柱下降，再指 Ours 两根绿柱也下降。停两秒让数字入镜。

On the twelve paired tasks, Batch 1 averaged **13,290** meta output tokens.

- Homogeneous control, Batch 2: **9,840 (−26.0%)**.
- Heterogeneous modification, Batch 2: **8,576 (−35.5%)**.

Direction matches the paper. Magnitude of the *relative* drop sits next to Opus (−31%), not Sonnet (−58%). Absolute counts are higher because DeepSeek plus XML prompting is more verbose than Claude — I will name the six causes in a minute.

**【切屏】** **Slide 5 Fig 2**. 指 Q0 / Q6 / Q7 / Q13 的绿柱塌下去。

Reuse is not uniform. Clean structural twins collapse:

- Q6 macro regression: **23,886 → 5,873 (−75%)**
- Q0 sentiment report: **19,974 → 5,357 (−73%)**
- Q7 Tetris → Snake: **5,731 → 1,652 (−71%)**, **zero new subagents**
- Q13 Tokyo → Paris itinerary: **20,159 → 6,093 (−70%)**

Web-heavy or schema-shift tasks stay flat or bounce: course pages, crypto, Weibo vs Mastodon, GitHub org HTML. That is expected: saved scrapers do not transfer when the site changes.

---

## 6:10–8:20  Isolated modification  *(Rubric 4)*

**【切屏】** **Slide 6 Modification**. 强调这句话：*only `SUBAGENT_*` changed; same 30-skill snapshot.*

The course requires an **isolated, measurable** change. Ours is architectural: keep DeepSeek as the cloud orchestrator, **offload 100% of subagent LLM calls** to local Qwen, and **disable thinking** so a 300–800 token cap is not eaten by hidden chain-of-thought.

Control and modified Batch 2 both start from the **same 30 skills** saved after Batch 1. Same skip list, same timeout policy. The only knob is `SUBAGENT_URL` / `SUBAGENT_MODEL`.

**【切屏】** **Slide 7 Fig 3**. 左图时间，右图 token 账单。

Measured impact on those 12 tasks:

| | Homogeneous DeepSeek sub | Local Qwen sub | Delta |
|---|---:|---:|---:|
| Completion | 12/12 | 12/12 | no drop |
| Meta tokens / task | 9,840 | **8,576** | **−12.8%** |
| Wall time | 70.8 min | **40.5 min** | **−42.8%** |
| Cloud subagent tokens | 373k | **0** | **−100% API cost** |

Local 27B was *faster* and *cheaper on the orchestrator*, not a quality sacrifice. Short extract-and-plot calls avoid WAN round-trips, and we saw fewer `modify_subagent` loops (15 vs 26).

---

## 8:20–11:00  Live evidence (this is the demo)

**【切屏】** 先 **Slide 8 Artifacts** 停留 10 秒，然后切文件夹 `04_Showcase_Artifacts/02_agent_generated_charts/`，点开 **B2_Q6_us_health_gdp_regression.png**。

This scatter is Batch 2 Q6 — US health spend vs GDP — produced by the **saved** `scatter_reg` skill, not a from-scratch rewrite. R² is 0.99; the skill’s `SKILL.md` even documents the newline-token trick that avoided JSON escaping bugs.

**【切屏】** 打开 `01_saved_subagent_skills/scatter_reg/SKILL.md`，滚到 Usage 的 XML 块，停 5 秒。

This is the paper’s unit of memory: not a paragraph in a scratchpad, a **callable Python entry file**.

**【切屏】** 打开 `03_agent_generated_reports_and_code/B2_Q7_snake_game_solution.py`，指 `class SnakeGame`。不要运行 Tk 窗口（无显示也可能卡住）。

Batch 2 Q7 reused the Tetris code-generator skill. Meta tokens: **1,652**. That is the cleanest “executable reuse” clip.

**【切屏】** 切 `03_Trajectory_Viewer.html`。点 **Preset 2 — Snake reuse**。展开第一两个 iteration，指 `list_saved_subagents` → `run_subagent`，没有 `create_subagent`。

Watch the trajectory, not the Python. Install-phase trajectories are long — Preset 1 sentiment is the from-scratch contrast. Preset 4 is our honest failure: Batch 1 Q2 diagnoses that Tencent Meeting needs QR login and **stops**. We did not fake a booking.

Optional if time ≥ 90s left: play `04_agent_generated_audio_previews/B2_Q11_focus_music_20s_preview.mp3` at low volume — agent built a 20-minute MP3 with PyAV because the host had no ffmpeg.

---

## 11:00–12:30  Why Table 1 does not match + debug diary

**【切屏】** 回到幻灯 **Slide 9 Why not exact** + **Slide 10 Debug**。

Six reasons absolute tokens exceed the paper:

1. DeepSeek leaks DSML tags and fails the skill-gate — 80+ “call `get_skill_description` first” bounces.
2. Different tokenizer, more verbose XML.
3. We saved **30 fine-grained skills**; retrieval itself costs tokens. When a skill actually fits, tokens collapse — Q7, Q8.
4. Web domain shift (Weibo, GitHub HTML).
5. Host was not the paper’s desktop: no Chrome profile, no ffmpeg.
6. `temperature=1.0` single trial — Q4 and Q6 flip between control and modified.

The worst production bug: local Qwen **thinking** ate `max_tokens`, returned empty `content`, and the client slept up to 60 seconds. Batch 1 Q10: **102 empty retries**, 50-minute timeout. Fix: `enable_thinking=False` plus no backoff on empty local replies. Batch 2: **zero timeouts**.

We also raised first-turn `max_tokens` from 200 to 4000, and changed the 60-iteration auto-stop from `return` to `break` so `trajectory.json` is always written.

---

## 12:30–13:10  Close

**【切屏】** **Slide 11 Takeaway**。脸可以半出镜。

What reproduces: executable subagent accumulation **does** cut orchestrator tokens — **−26%** homogeneous, **−35%** with local Qwen — on the same 12-task pair.

What does not: Claude-scale absolute counts, and login-walled sites.

Practical takeaway: split the **orchestration plane** (cloud flash model) from the **execution plane** (local 27B, thinking off). We kept 12/12 completion, cut Batch-2 wall time **43%**, and billed **zero** subagent API tokens.

Happy to take questions — report PDF is in this folder.

---

## If you run long (cut in this order)

1. Skip audio clip.
2. Skip SKILL.md scroll; keep Snake trajectory.
3. Skip Fig 2; keep Fig 1 + Fig 3.

## If asked in Q&A

- **“Did you match Table 1?”** Direction yes; absolute no. Edge Case A. Same metric, different tokenizer.
- **“Is local Qwen worse?”** Not on this suite. Faster, fewer modify loops, 12/12.
- **“Why skip Q2/Q10/Q12?”** External blockers, documented in the report, not metric gaming. Batch 1 still ran them.
- **“What is a meta token?”** Orchestrator `completion_tokens` only. Subagent LLM is counted separately; local Qwen sub tokens are not a cloud bill.
