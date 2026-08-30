# Speech Translator

Real-time speech translation web app. Speak into your mic in any language, get the
translated text and a spoken translation back — powered by Google's speech
recognition/translate and gTTS, served through a FastAPI backend to a React frontend.

## Stack

- **Frontend**: React (Vite) — records mic audio via the browser `MediaRecorder` API
- **Backend**: FastAPI — decodes audio (via `pydub`/ffmpeg), transcribes it
  (`speechrecognition` + Google), translates it (`deep-translator`), and synthesizes
  speech (`gTTS`)

## Prerequisites

- Python 3.11+
- Node.js 18+
- [ffmpeg](https://ffmpeg.org/download.html) on your `PATH` (needed to decode the
  browser-recorded audio before transcription)

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

The backend needs a real server (it shells out to `ffmpeg` and makes live calls to
Google's translate/speech/TTS), so it can't be hosted as a static site. The frontend
is just a static build, so it's deployed separately.

### 1. Backend → Render

1. Push this repo to GitHub (see below).
2. In Render: **New → Blueprint**, point it at this repo. It'll pick up
   [`render.yaml`](render.yaml) automatically, which builds `backend/Dockerfile`
   (installs `ffmpeg` — Render's native Python runtime doesn't include it, hence
   Docker) and deploys it as a free web service.
3. Once deployed, copy the service URL Render gives you
   (e.g. `https://speech-translator-backend.onrender.com`).

Render's free tier spins the service down after inactivity, so the first request
after a while can take 30-60s to wake up — normal for a portfolio demo.

### 2. Frontend → Vercel

1. In Vercel: **New Project**, import the same GitHub repo.
2. Set **Root Directory** to `frontend` (this is a monorepo — Vercel needs to know
   where the actual app lives).
3. Vercel auto-detects Vite; leave the build settings as-is.
4. Add an environment variable: `VITE_API_URL` = the Render URL from step 1.
5. Deploy. Vercel gives you an HTTPS URL — required for microphone access to work
   in the browser (only `localhost` and HTTPS origins are allowed to use
   `getUserMedia`).

### 3. Connect them

Back in Render, set the `ALLOWED_ORIGINS` environment variable to your Vercel URL
(e.g. `https://speech-translator.vercel.app`) so the backend's CORS policy accepts
requests from it, then redeploy the backend service.

### Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create speech-translator --public --source=. --remote=origin --push
# or, without gh: create the repo on github.com first, then:
# git remote add origin https://github.com/<you>/speech-translator.git
# git push -u origin main
```
