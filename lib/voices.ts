export interface Voice {
  id: string;
  label: string;
  language: string;
  /** Which TTS provider D-ID should use to synthesize this voice_id. */
  provider: string;
}

// A small starter set covering English and Hebrew. Add more Microsoft
// neural voice_ids here to expand the selector later.
export const VOICES: Voice[] = [
  { id: "en-US-JennyNeural", label: "English (US) - Jenny", language: "en-US", provider: "microsoft" },
  { id: "en-US-GuyNeural", label: "English (US) - Guy", language: "en-US", provider: "microsoft" },
  { id: "he-IL-HilaNeural", label: "Hebrew - Hila", language: "he-IL", provider: "microsoft" },
  { id: "he-IL-AvriNeural", label: "Hebrew - Avri", language: "he-IL", provider: "microsoft" },
];

export const DEFAULT_VOICE_ID = VOICES[0].id;

export function getVoiceById(id: string): Voice | undefined {
  return VOICES.find((voice) => voice.id === id);
}
