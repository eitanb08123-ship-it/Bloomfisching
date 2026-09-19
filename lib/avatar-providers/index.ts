import { AvatarProvider, ProviderError } from "./types";
import { DidAvatarProvider } from "./did";
import { MockAvatarProvider } from "./mock";

export * from "./types";

/**
 * Adapter factory: swapping providers (e.g. to HeyGen or Synthesia) means
 * adding a new class that implements AvatarProvider and a case here -
 * nothing else in the app needs to change.
 */
export function getAvatarProvider(): AvatarProvider {
  const providerName = process.env.AVATAR_PROVIDER || "did";

  switch (providerName) {
    case "did":
      return new DidAvatarProvider(
        process.env.DID_API_KEY || "",
        process.env.DID_API_BASE_URL || "https://api.d-id.com",
      );
    case "mock":
      return new MockAvatarProvider();
    default:
      throw new ProviderError(`Unknown AVATAR_PROVIDER "${providerName}".`, 500);
  }
}
