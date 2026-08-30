# Speech Translator

Real-time speech translation web app. Speak into your mic in any language, get the
translated text and a spoken translation back — powered by Google's speech
recognition/translate and gTTS, served through a FastAPI backend to a React frontend.

## Stack

- **Frontend**: React (Vite) — records mic audio via the browser `MediaRecorder` API
- **Backend**: FastAPI — decodes audio (via `pydub` + a bundled portable `ffmpeg`
  binary, no system install needed), transcribes it (`speechrecognition` + Google),
  translates it (`deep-translator`), and synthesizes speech (`gTTS`)

## Prerequisites

- Python 3.11+
- Node.js 18+

(No system ffmpeg install needed — `imageio-ffmpeg` bundles a portable binary as a
pip dependency, so decoding works the same locally and on serverless hosts.)

## Run it

**Backend**

```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload
```

**Frontend** (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (defaults to `http://localhost:5173`, this project runs on
`5174` — see `.claude/launch.json`), pick a target language, tap the mic, and speak.
Allow microphone access when your browser asks.

If your frontend runs on a different port, add it to `allow_origins` in
`backend/app/main.py`, and update `frontend/.env` (`VITE_API_URL`) if the backend
isn't on `http://127.0.0.1:8001`.

## Deploying

The backend is deployed as **Vercel serverless Python functions** (`backend/api/index.py`
+ `backend/vercel.json`), the frontend as a static build on **Netlify**.

### 1. Push to GitHub

```bash
git init          # already done if you're continuing this project
git add .
git commit -m "Initial commit"
gh repo create speech-translator --public --source=. --remote=origin --push
# or, without gh: create the repo on github.com first, then:
# git remote add origin https://github.com/<you>/speech-translator.git
# git push -u origin main
```

### 2. Backend → Vercel

1. In Vercel: **New Project**, import the `speech-translator` repo.
2. Set **Root Directory** to `backend` (this is a monorepo — Vercel needs to know
   where the actual app lives).
3. Vercel auto-detects `backend/api/index.py` as a catch-all Python function
   (it natively serves everything under `/api/*` to that one FastAPI app — no
   custom rewrites needed; a `rewrites` rule that redirects to a fixed
   destination actually breaks this, since it overwrites the real request
   path instead of passing it through).
4. Deploy. Copy the resulting URL, e.g. `https://speech-translator-api.vercel.app`.

**Known limits of this setup** (inherent to serverless, not fixable by config):
- **Execution time**: Vercel's Hobby plan caps function duration at 10s. Translation
  and TTS calls are normally fast, but a slow network hop to Google occasionally
  pushes close to that limit — if you hit timeouts under real use, Vercel Pro raises
  it to 60s+.
- **Cold starts**: the first request after idle time takes longer (loading
  `speechrecognition`/`pydub`/etc. from scratch). Normal for a portfolio demo.
- **No persistent cache**: the in-memory translation cache resets between cold
  starts, unlike a long-running server.

### 3. Frontend → Netlify

1. In Netlify: **Add new site → Import an existing project**, pick the same repo.
2. **Base directory**: `frontend`. **Build command**: `npm run build`.
   **Publish directory**: `frontend/dist`.
3. Under **Site configuration → Environment variables**, add:
   - `VITE_API_URL` = the Vercel URL from step 2.
4. Deploy. Netlify gives you an HTTPS URL — required for microphone access (only
   `localhost` and HTTPS origins may use `getUserMedia`).

### 4. Connect them

Back in Vercel, open the backend project → **Settings → Environment Variables**, add:
- `ALLOWED_ORIGINS` = your Netlify URL (e.g. `https://speech-translator.netlify.app`)

Redeploy the backend so the new CORS origin takes effect.

### Alternative: Docker-based hosts (Render, Fly.io, Cloud Run)

`backend/Dockerfile` still works standalone if you'd rather run this as a normal
long-lived server instead of serverless functions — no execution-time limits, no
cold starts. `render.yaml` is included for one-click deploy on Render specifically.
The exact same `imageio-ffmpeg`-bundled decoding path is used either way, so
behavior is identical.
