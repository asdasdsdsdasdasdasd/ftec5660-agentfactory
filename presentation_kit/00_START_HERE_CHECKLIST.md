# Zoom Recording Checklist (≤15 min)

Open this folder in a file manager. **Do not share `.env` or any API key.**

## 1. Fill identity (before recording)

In `../report/REPRODUCIBILITY_REPORT.md`, replace `[Your Name]` and `[Your Student ID]`.  
If you change them after generating the PDF, regenerate:

```bash
cd /mnt/d/openclaw/AgentFactory
# optional: python3 -m markdown report/REPRODUCIBILITY_REPORT.md
# then print HTML → PDF from the browser
```

A copy of the current PDF is already here: `05_REPRODUCIBILITY_REPORT.pdf`.

## 2. Files to share on Zoom (keep these three tabs open)

| Tab | File | When |
|---|---|---|
| **A. Slides** | `02_Interactive_Presentation_Slides.html` | Whole talk. Arrow keys / click dots. |
| **B. Trajectory viewer** | `03_Trajectory_Viewer.html` | Minute ~8. Four preset buttons, no server needed. |
| **C. Artifacts** | `04_Showcase_Artifacts/index.html` | Charts, Snake `.py`, Paris itinerary, 20s audio. This is a **folder**; open the `index.html` inside it, do not try to open the folder as a file. |

Open HTML with a double-click (`file://`). If a browser blocks local JS, from this folder run:

```bash
python3 -m http.server 8765
# then visit http://127.0.0.1:8765/02_Interactive_Presentation_Slides.html
```

## 3. Recording flow (matches `01_ZOOM_SPEAKER_SCRIPT.md`)

- [ ] Timer on phone: **13:00 speak + 2:00 buffer**
- [ ] Share **entire screen** (so you can switch tabs)
- [ ] Mute system notifications
- [ ] Camera on, slides at 100% zoom
- [ ] Spoken language: **English** (script is English). Chinese lines in the script are *cut-screen cues only* — do not read them aloud
- [ ] Hit the four rubric boxes in order: paper → setup → numbers → isolated modification
- [ ] Show at least one **live artifact** (Q6 scatter PNG or Snake `.py`) and one **trajectory preset** (Preset 2 Snake reuse)
- [ ] Say Q2/Q10/Q12 were **scoped out**, not hidden
- [ ] Stop at 13:00 even if you skip the last artifact

## 4. Do / Don't on camera

**Do:** Fig 1, Fig 3, Preset 2 (Snake, 1,652 tokens), `scatter_reg/SKILL.md`, Paris itinerary, 20s focus-audio clip.

**Don't:** scroll `llm.py`, open `.env`, claim Table 1 absolute tokens match Claude, pretend Q2 logged into Tencent Meeting.

## 5. After recording

- [ ] Export MP4 / Zoom cloud link
- [ ] Confirm report PDF ≤10 pages
- [ ] GitHub: README + commits, **no secrets** (only push if you have a repo name)
