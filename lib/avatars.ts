export interface Avatar {
  id: string;
  name: string;
  imageUrl: string;
}

// D-ID's publicly-hosted sample presenters - free to use for the "default
// avatar" starting point. Add more here to expand the gallery later.
export const AVATARS: Avatar[] = [
  {
    id: "noelle",
    name: "Noelle",
    imageUrl: "https://create-images-results.d-id.com/DefaultPresenters/Noelle_f/image.png",
  },
  {
    id: "emma",
    name: "Emma",
    imageUrl: "https://create-images-results.d-id.com/DefaultPresenters/Emma_f/image.jpeg",
  },
];

export const DEFAULT_AVATAR_ID = AVATARS[0].id;

export function getAvatarById(id: string): Avatar | undefined {
  return AVATARS.find((avatar) => avatar.id === id);
}
