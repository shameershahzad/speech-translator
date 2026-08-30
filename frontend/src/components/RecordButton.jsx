const LABELS = {
  idle: "Tap to speak",
  recording: "Listening… tap to stop",
  processing: "Working on it…",
};

export default function RecordButton({ status, onClick, elapsedSeconds }) {
  const isRecording = status === "recording";
  const isProcessing = status === "processing";

  return (
    <div className="record-control">
      <button
        type="button"
        className={`record-button record-button--${status}`}
        onClick={onClick}
        disabled={isProcessing}
        aria-label={LABELS[status]}
      >
        {isRecording && <span className="record-button__ring" />}
        <MicIcon spinning={isProcessing} />
      </button>
      <p className="record-control__status">
        {isRecording ? `${LABELS.recording} · ${elapsedSeconds}s` : LABELS[status]}
      </p>
    </div>
  );
}

function MicIcon({ spinning }) {
  return (
    <svg
      className={spinning ? "mic-icon mic-icon--spin" : "mic-icon"}
      width="30"
      height="30"
      viewBox="0 0 24 24"
      fill="none"
    >
      {spinning ? (
        <path
          d="M12 3a9 9 0 1 0 9 9"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      ) : (
        <>
          <rect x="9" y="2" width="6" height="12" rx="3" fill="currentColor" />
          <path
            d="M5 11a7 7 0 0 0 14 0M12 18v3"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </>
      )}
    </svg>
  );
}
