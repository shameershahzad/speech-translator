export default function LanguageSelector({ languages, value, onChange, disabled, label = "Translate into" }) {
  return (
    <label className="language-selector">
      <span className="language-selector__label">{label}</span>
      <select
        className="language-selector__select"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
      >
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.name}
          </option>
        ))}
      </select>
    </label>
  );
}
