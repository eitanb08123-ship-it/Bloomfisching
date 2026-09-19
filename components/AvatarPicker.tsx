"use client";

import type { Avatar } from "@/lib/avatars";

interface AvatarPickerProps {
  avatars: Avatar[];
  selectedId: string;
  onSelect: (id: string) => void;
  disabled?: boolean;
}

export function AvatarPicker({ avatars, selectedId, onSelect, disabled }: AvatarPickerProps) {
  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
      {avatars.map((avatar) => {
        const isSelected = avatar.id === selectedId;
        return (
          <button
            key={avatar.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(avatar.id)}
            aria-pressed={isSelected}
            className={`flex flex-col items-center gap-2 rounded-lg border-2 p-2 text-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
              isSelected
                ? "border-indigo-600 bg-indigo-50"
                : "border-transparent bg-white hover:border-slate-300"
            }`}
          >
            <span className="relative block h-20 w-20 overflow-hidden rounded-full bg-slate-100">
              {/* eslint-disable-next-line @next/next/no-img-element -- avatar hosts vary and aren't known at build time */}
              <img src={avatar.imageUrl} alt={avatar.name} className="h-full w-full object-cover" />
            </span>
            <span className="font-medium">{avatar.name}</span>
          </button>
        );
      })}
    </div>
  );
}
