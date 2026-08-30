import { useEffect, useMemo, useRef, useState } from "react";
import LanguageSelector from "./components/LanguageSelector";
import RecordButton from "./components/RecordButton";
import ResultPanel from "./components/ResultPanel";
import { fetchLanguages, speechToText, textToSpeechUrl, translateText } from "./api";
import "./App.css";

const DEFAULT_LANGUAGE = { code: "fr", name: "French" };
const DEFAULT_SOURCE_LANGUAGE = { code: "en", name: "English" };

// The backend decodes audio with an explicit codec (no ffprobe available on
// serverless hosts), so it needs to know exactly what the browser recorded.
// Preference order matters: Chrome/Firefox/Edge support webm/opus, Safari
// only supports mp4/aac.
const PREFERRED_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
];

function pickSupportedMimeType() {
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) return undefined;
  return PREFERRED_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
}

export default function App() {
  const [languages, setLanguages] = useState([DEFAULT_LANGUAGE]);
  const [targetLang, setTargetLang] = useState(DEFAULT_LANGUAGE.code);
  const [sourceLang, setSourceLang] = useState(DEFAULT_SOURCE_LANGUAGE.code);
  const [status, setStatus] = useState("idle"); // idle | recording | processing
  const [sourceText, setSourceText] = useState("");
  const [translatedText, setTranslatedText] = useState("");
  const [error, setError] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [playing, setPlaying] = useState(false);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => {
    fetchLanguages()
      .then((list) => {
        if (list.length) {
          setLanguages(list);
          if (!list.some((lang) => lang.code === targetLang)) {
            setTargetLang(list[0].code);
          }
        }
      })
      .catch(() => setError("Could not reach the translator backend. Is it running?"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const targetLanguageName = useMemo(
    () => languages.find((lang) => lang.code === targetLang)?.name ?? targetLang,
    [languages, targetLang]
  );

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream, { mimeType: pickSupportedMimeType() });
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = handleRecordingStop;

      mediaRecorderRef.current = recorder;
      recorder.start();
      setStatus("recording");
      setElapsedSeconds(0);
      timerRef.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    } catch {
      setError("Microphone access was blocked or unavailable. Allow mic permissions and try again.");
    }
  };

  const stopRecording = () => {
    clearInterval(timerRef.current);
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    setStatus("processing");
  };

  const handleRecordingStop = async () => {
    const mimeType = mediaRecorderRef.current?.mimeType || "audio/webm";
    const blob = new Blob(chunksRef.current, { type: mimeType });
    try {
      const heard = await speechToText(blob, mimeType, sourceLang);
      setSourceText(heard);
      const translated = await translateText(heard, targetLang);
      setTranslatedText(translated);
    } catch (err) {
      setError(err.message || "Something went wrong while translating.");
    } finally {
      setStatus("idle");
    }
  };

  const handleMicClick = () => {
    if (status === "recording") {
      stopRecording();
    } else if (status === "idle") {
      startRecording();
    }
  };

  const playTranslation = () => {
    if (!translatedText) return;
    setError(null);
    const audio = new Audio(textToSpeechUrl(translatedText, targetLang));
    audioRef.current = audio;
    setPlaying(true);
    audio.play().catch(() => setPlaying(false));
    audio.onended = () => setPlaying(false);
    audio.onerror = () => {
      setPlaying(false);
      setError(`Spoken audio isn't available for ${targetLanguageName} yet.`);
    };
  };

  return (
    <div className="app">
      <div className="app__glow" aria-hidden="true" />
      <header className="app__header">
        <span className="app__badge">React · FastAPI · Google Translate</span>
        <h1 className="app__title">Speech Translator</h1>
        <p className="app__subtitle">
          Speak in any language, hear it back instantly in {targetLanguageName}.
        </p>
      </header>

      <main className="app__card">
        <div className="app__language-row">
          <LanguageSelector
            label="Speak in"
            languages={languages}
            value={sourceLang}
            onChange={setSourceLang}
            disabled={status !== "idle"}
          />
          <LanguageSelector
            label="Translate into"
            languages={languages}
            value={targetLang}
            onChange={setTargetLang}
            disabled={status !== "idle"}
          />
        </div>

        <RecordButton status={status} onClick={handleMicClick} elapsedSeconds={elapsedSeconds} />

        {error && <div className="app__error">{error}</div>}

        <div className="app__results">
          <ResultPanel
            title="You said"
            text={sourceText}
            placeholder="Your recognized speech will appear here."
            accent="source"
          />
          <ResultPanel
            title={`Translation (${targetLanguageName})`}
            text={translatedText}
            placeholder="Your translation will appear here."
            onPlay={playTranslation}
            playing={playing}
            accent="target"
          />
        </div>
      </main>

      <footer className="app__footer">
        Built with React, FastAPI, SpeechRecognition &amp; gTTS.
      </footer>
    </div>
  );
}
