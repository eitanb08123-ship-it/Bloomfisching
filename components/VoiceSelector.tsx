"use client";

import type { Voice } from "@/lib/voices";

interface VoiceSelectorProps {
  voices: Voice[];
  selectedId: string;
  onSelect: (id: string) => void;
  disabled?: boolean;
}

export function VoiceSelector({ voices, selectedId, onSelect, disabled }: VoiceSelectorProps) {
  return (
    <select
      value={selectedId}
      disabled={disabled}
      onChange={(event) => onSelect(event.target.value)}
      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
    >
      {voices.map((voice) => (
        <option key={voice.id} value={voice.id}>
          {voice.label}
        </option>
      ))}
    </select>
  );
}
