---
name: run
description: Launch gainbridge's backend (FastAPI) and frontend (Vite/React) dev servers and drive the UI with Playwright for verification. Use whenever asked to run, start, or screenshot the app, or to confirm a frontend/backend change works end to end.
---

# Running gainbridge

## Dev servers

Backend (FastAPI, port 8000). Run from `backend/` — `app/core/config.py`
loads `env_file="../.env"` relative to that cwd, so the repo-root `.env`
is picked up automatically. No symlink or extra setup needed.

```bash
cd backend && uv run fastapi dev app/main.py --port 8000
```

Health check: `curl -sf http://localhost:8000/api/v1/utils/health-check/`

Frontend (Vite, port 5173):

```bash
cd frontend && bun run dev --port 5173
```

Wait for both with polling, not `sleep`:

```bash
timeout 30 bash -c 'until curl -sf http://localhost:8000/api/v1/utils/health-check/ >/dev/null; do sleep 1; done'
timeout 30 bash -c 'until curl -sf http://localhost:5173 >/dev/null; do sleep 1; done'
```

Stop by killing the port's listener (not `pkill -f`, which can match the
agent's own process):

```bash
lsof -ti:8000 -sTCP:LISTEN | xargs -r kill
lsof -ti:5173 -sTCP:LISTEN | xargs -r kill
```

## Driving the UI with Playwright

The devcontainer's `postCreateCommand` (`.devcontainer/devcontainer.json`)
runs `cd frontend && bunx playwright install --with-deps chromium` at
container creation, so a matching Chromium build is already installed —
**do not re-run `playwright install`** to fix a browser-launch error; see
the gotcha below for what the real fix usually is.

**Gotcha — run driver scripts from inside the repo tree, never from
`/tmp` or a scratchpad path.** Node/Bun resolves a bare `import
"playwright"` starting from the *importing script's own directory*, not
the shell's cwd. A script placed in `/tmp/.../scratchpad` (outside the
repo) can't see `frontend/node_modules` or the repo root's
`node_modules`, where the pinned `playwright-core` lives — the version
the devcontainer actually installed a browser for. When that happens,
Bun silently resolves/fetches a *different* `playwright-core` from its
own global cache instead of failing clearly, and that version has no
matching browser installed. The resulting error —
`Executable doesn't exist at .../chromium_headless_shell-<rev>` — reads
exactly like "Chromium isn't installed," and Playwright's own message
even suggests `playwright install`, but that's the wrong fix: the
browser is already there for the right version, just not the version
this particular script accidentally resolved.

**Fix:** write the driver script inside the repo (e.g. a throwaway file
at the repo root, or under `frontend/`), run it with `bun run
<path-to-script>`, and delete it when done. Never diagnose a
"Executable doesn't exist" error by reinstalling before checking where
the script lives and whether the revision number in the error matches
what's already cached at `~/.cache/ms-playwright/`.

Minimal driver pattern (adapt paths/actions per task):

```js
import { chromium } from "playwright"

const browser = await chromium.launch({ args: ["--no-sandbox"] })
const page = await (await browser.newContext()).newPage()

page.on("pageerror", (err) => console.log("[pageerror]", err.message))
page.on("console", (msg) => {
  if (msg.type() === "error") console.log("[console:error]", msg.text())
})

await page.goto("http://localhost:5173", { waitUntil: "domcontentloaded" })
await page.waitForSelector('button:has-text("Add Source")', { timeout: 15000 })
await page.screenshot({ path: "/absolute/path/to/scratchpad/out.png" })

await browser.close()
```

Run it with `bun run ./drive.mjs` from inside the repo (e.g. repo root).
Screenshots can still be written to the scratchpad directory — only the
*script itself* needs to live inside the repo tree, for module
resolution.
