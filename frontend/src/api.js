const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8001";

async function parseErrorMessage(response) {
  try {
    const body = await response.json();
    return body.detail || response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function fetchLanguages() {
  const response = await fetch(`${API_URL}/api/languages`);
  if (!response.ok) throw new Error(await parseErrorMessage(response));
  return response.json();
}

export async function speechToText(audioBlob, mimeType) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "speech");
  if (mimeType) formData.append("mime_type", mimeType);
  const response = await fetch(`${API_URL}/api/speech-to-text`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw new Error(await parseErrorMessage(response));
  const data = await response.json();
  return data.text;
}

export async function translateText(text, targetLang) {
  const response = await fetch(`${API_URL}/api/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, target_lang: targetLang }),
  });
  if (!response.ok) throw new Error(await parseErrorMessage(response));
  const data = await response.json();
  return data.translated_text;
}

export function textToSpeechUrl(text, lang) {
  const params = new URLSearchParams({ text, lang });
  return `${API_URL}/api/text-to-speech?${params.toString()}`;
}
