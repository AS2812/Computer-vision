function localApiBase(): string {
  if (typeof window === "undefined") return "http://127.0.0.1:8765";
  return `${window.location.protocol}//${window.location.hostname}:8765`;
}

const configuredApiBase = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "");

export const apiBase: string | null =
  configuredApiBase === "same-origin"
    ? ""
    : configuredApiBase || (import.meta.env.DEV ? localApiBase().replace(/\/$/, "") : null);
