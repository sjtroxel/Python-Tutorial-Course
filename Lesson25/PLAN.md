# Lesson 25 — Add Tailwind v4 + a motion library to the Flask weather app

**Goal:** take the working Lesson 23 weather app (copied here) and re-skin it with
**Tailwind CSS v4** for styling and a **framework-agnostic JS motion library** for
animation. The *point* of the exercise is to bank the integration recipe — how
Tailwind and a motion lib wire into a server-rendered Python app — so it transfers
to Flask, Django, FastAPI+Jinja, or anything else that serves HTML.

This is a 1-day rep (Wed 2026-06-10), the gap day before the AI Masterclass restarts Thu 6/11.

---

## What's already done (Python side — don't redo)

- Full copy of Lesson 23: `server.py`, `weather.py`, 3 templates, `static/styles/style.css`,
  both test files, `.env` (holds `API_KEY`).
- Own venv at `Lesson25/.venv` with the Flask stack + pytest installed; `requirements.txt` re-frozen.
- Copied tests verified green in this folder (10 passed).

Run the app:    `Lesson25/.venv/bin/python server.py`  → http://localhost:8000
Run the tests:  `Lesson25/.venv/bin/python -m pytest -q`

> Note: Tailwind and the motion library are **not** pip packages, so `requirements.txt`
> stays Python-only. Tailwind v4 ships as a **standalone binary** (no Node/npm), and the
> motion lib loads from a **CDN `<script>`**. Nothing new goes into the venv.

---

## Decisions locked

| Choice | Decision | Why |
|---|---|---|
| Tailwind version | **v4** (current major) | You asked for v4. It's CSS-first config, not the old `tailwind.config.js`. |
| Tailwind install path | **Standalone CLI binary** | No Node, no `node_modules`, no bundler. Cleanest for Flask. |
| Motion library | **GSAP** (default) — see alt below | Loads from one CDN `<script>`, works on *any* HTML page regardless of backend, industry-standard, free. |

**Motion alternative — pick at the start of the session:** If you'd rather use something
that feels like the **Framer Motion** you used in Heritage Odyssey, use **Motion
(motion.dev)** — it's the vanilla-JS successor by the same author, similar `animate()` API.
Wiring is slightly fiddlier (ES-module import from CDN) than GSAP's plain global script.
Either one is 100% framework-agnostic; the recipe below shows GSAP, with the Motion
swap noted.

---

## Part A — Tailwind v4 via the standalone CLI

> ⚠️ **Verify the current download first** — binary names/versions move. Grab the latest
> from the official releases page (`github.com/tailwindlabs/tailwindcss/releases/latest`)
> and pick the Linux x64 asset. Check `tailwindcss.com` v4 docs for any syntax drift before copying commands below.

1. **Download the binary** into `Lesson25/` (example — confirm the current asset name):
   ```bash
   cd Lesson25
   curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
   chmod +x tailwindcss-linux-x64
   ```
   (Add `tailwindcss-linux-x64` to `.gitignore` thinking, or just leave it local — it's a
   ~100MB binary, don't commit it. The root `.gitignore` doesn't cover it yet.)

2. **Create the input CSS** at `static/src/input.css`:
   ```css
   @import "tailwindcss";

   /* v4 is CSS-first: define design tokens here instead of tailwind.config.js */
   @theme {
     --color-brand: #38bdf8;
     --font-display: "Segoe UI", system-ui, sans-serif;
   }

   /* Tell v4 which files to scan for class names (the "content" step). */
   @source "../../templates/**/*.html";
   ```

3. **Build/watch** — generates the real stylesheet into `static/styles/`:
   ```bash
   ./tailwindcss-linux-x64 -i ./static/src/input.css -o ./static/styles/output.css --watch
   ```
   Leave this running in one terminal; run Flask in another.

4. **Link the output** in each template `<head>` (replace, or sit alongside, the existing
   `style.css` link):
   ```html
   <link href="{{ url_for('static', filename='styles/output.css') }}" rel="stylesheet" />
   ```

5. **Re-skin with utility classes.** Start with `templates/index.html` — e.g. swap the bare
   `<body>`/`<h1>`/`<form>` for Tailwind utilities (`min-h-screen bg-slate-800 text-slate-100
   flex flex-col items-center gap-8 p-8`, etc.). Then `weather.html` and `city-not-found.html`.

### The one real gotcha to bank (Jinja + purge)

Tailwind only keeps classes it **literally sees as complete strings** in the files named by
`@source`. So a dynamically built class in Jinja —
```html
<p class="text-{{ color }}-500">   {# ❌ gets stripped, style silently missing #}
```
— won't survive the build. Fixes: write the **full** class name, branch in the template
(`{% if cold %}text-blue-500{% else %}text-red-500{% endif %}`), or safelist it with
v4's `@source inline("text-blue-500 text-red-500");`. This is the same lesson as React,
just easy to hit inside `{% for %}` loops.

---

## Part B — Motion library (GSAP default)

1. **Load GSAP from a CDN** in the template `<head>` (verify current latest tag):
   ```html
   <script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
   ```

2. **Animate something** with a small script before `</body>`:
   ```html
   <script>
     // fade + rise the heading on load
     gsap.from("h1", { y: -20, opacity: 0, duration: 0.6, ease: "power2.out" });
     // pop the weather card if present
     gsap.from(".weather-card", { scale: 0.9, opacity: 0, duration: 0.5, delay: 0.2 });
   </script>
   ```
   Wrap the weather readout in `weather.html` in a `<div class="weather-card ...">` so there's
   a target.

3. **Why this is the universal recipe:** GSAP is just a `<script>` on an HTML page. It has no
   idea Flask rendered the page — so the *identical* snippet works in Django templates,
   FastAPI + Jinja2, or a static `.html`. That's the transferable trick: **server framework
   renders the HTML; the motion lib animates it client-side; the two never touch.**

### Motion (motion.dev) swap — if you chose the Framer-style option

```html
<script type="module">
  import { animate } from "https://cdn.jsdelivr.net/npm/motion@latest/+esm";
  animate("h1", { opacity: [0, 1], y: [-20, 0] }, { duration: 0.6 });
</script>
```
Note the `type="module"` + ESM import — that's the only structural difference from GSAP.

---

## Suggested order for the morning

1. Pick the motion lib (GSAP unless you want the Framer feel).
2. Get the Tailwind CLI binary downloaded + `--watch` running; confirm `output.css` appears.
3. Re-skin `index.html` first; eyeball it at localhost:8000 until the build pipeline clearly works.
4. Re-skin `weather.html` + `city-not-found.html`.
5. Add the motion lib + one animation per page.
6. Run the tests — **they assert on text content** (`b"Get Weather Conditions"`,
   `b"London Weather"`, etc.), so restyling shouldn't break them. If a test goes red, you
   changed copy/structure the test relied on; that's useful signal, not a Tailwind problem.
7. Decide what (if anything) to commit. The binary and `static/src/` are build inputs;
   `output.css` is a build artifact — your call whether to track it.

## Verification checklist

- [ ] `output.css` regenerates when you edit a template (watch is working)
- [ ] Pages visually restyled at http://localhost:8000
- [ ] At least one animation fires on each page
- [ ] `pytest -q` still green
- [ ] No dynamic-Jinja-class styles silently missing (the purge gotcha)

## Stretch (only if time)

- A `@theme` custom color used across all three pages (proves the v4 token system).
- A scroll- or hover-triggered animation, not just on-load.
- A tiny production build note: drop `--watch`, run once minified, compare file size vs the CDN Play approach.

---

### The reusable recipe (the thing to actually remember)

1. **Tailwind v4 + Python = standalone binary** (no Node), `@import "tailwindcss"`,
   `@source` your templates, `--watch` → `static/`. CSS-first config via `@theme`.
2. **Purge sees only literal class strings** — no string-built Jinja classes (or safelist them).
3. **Motion lib is backend-agnostic** — a CDN `<script>` that animates whatever HTML the
   Python framework rendered. Same code in Flask / Django / FastAPI.
