export default function ResultPanel({ title, text, placeholder, onPlay, playing, accent }) {
  const hasText = Boolean(text);

  return (
    <div className={`result-panel result-panel--${accent}`}>
      <div className="result-panel__header">
        <span className="result-panel__title">{title}</span>
        {hasText && onPlay && (
          <button
            type="button"
            className="result-panel__play"
            onClick={onPlay}
            disabled={playing}
            aria-label={`Play ${title}`}
          >
            {playing ? "▶ Playing…" : "▶ Play"}
          </button>
        )}
      </div>
      <p className={hasText ? "result-panel__text" : "result-panel__text result-panel__text--empty"}>
        {hasText ? text : placeholder}
      </p>
    </div>
  );
}
