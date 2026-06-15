[English](README.md) | [中文](README.zh-CN.md)

# KeleClaw Scout · Football Lookalike Trading Card

A [Hermes](https://github.com/lobstaff) agent skill: send a selfie, and the
assistant tells you which **football (soccer) star** you resemble, writes a
playful roast, and renders it as a **FIFA-style trading card** sent right back
to you in chat.

## What it does

1. You send a face selfie to your assistant and ask for a "球星撞型" (star lookalike).
2. The agent (gpt-5.5, multimodal) looks at the photo and figures out: your
   lookalike star, their position, their visual vibe, a match score, and a roast.
3. `generate_card.py` calls `gpt-image-2` to paint an **homage** card portrait
   (a generic, non-identifiable figure matching the star's vibe — never the real
   star's photo, never your face), then composites the text with Source Han Sans.
4. The finished card image is sent back to you.

## Install

Just tell your assistant:

> 帮我安装球星撞型 / install the football lookalike skill

Behind the scenes the assistant registers this repo as a skill source and
installs it via Hermes' native skill manager:

```
hermes skills tap add lobstaff/kele-scout
hermes skills install kele-scout
```

It installs into the assistant's own skills directory (persisted on its
volume) — **opt-in, per assistant**, not baked into the base image.

## How it works

- `SKILL.md` — instructions the agent reads (when to trigger, safety rails, flow).
- `generate_card.py` — the renderer: `gpt-image-2` card art + PIL text overlay.
  Fonts (Source Han Sans) auto-download to a cache on first run.

## Safety

- **Minors**: if the subject looks like a child/teen, the agent switches to a
  warm, encouraging mode — praise only, never a roast of appearance.
- **Roast line**: ribbing targets vibe / aura / "playing style" only — never
  real appearance, body, age, race, or gender.
- **Privacy & likeness**: the card uses an AI-generated homage figure — never
  your real face, never a real player's photo.

## Requirements

Runs inside a Hermes pod with keleclaw inference credentials in the environment
(`OPENAI_API_KEY` / `OPENAI_BASE_URL`) and Python 3 + Pillow.
