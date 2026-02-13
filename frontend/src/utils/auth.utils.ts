import { STORAGE_KEYS } from "../constants";

export const getAuthToken = (): string | null => {
  return localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
};

export const setAuthToken = (token: string): void => {
  localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);
};

export const removeAuthToken = (): void => {
  localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
};

export const isAuthenticated = (): boolean => {
  return getAuthToken() !== null;
};

/** Decode JWT payload and return email (sub claim). Returns null if no token or decode fails. */
export const getEmailFromToken = (): string | null => {
  const token = getAuthToken();
  if (!token) return null;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = parts[1];
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + (4 - base64.length % 4) % 4, "=");
    const decoded = atob(padded);
    const data = JSON.parse(decoded) as { sub?: string };
    return data.sub ?? null;
  } catch {
    return null;
  }
};





