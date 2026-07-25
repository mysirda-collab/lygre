import { apiUrl } from '@/lib/api';

export type AuthUser = {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'manager' | 'worker';
};

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
};

const ACCESS_TOKEN_KEY = 'lygre_access_token';
const REFRESH_TOKEN_KEY = 'lygre_refresh_token';
const USER_KEY = 'lygre_user';

export function getStoredAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function storeAuth(payload: LoginResponse): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, payload.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, payload.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
  document.cookie = `${ACCESS_TOKEN_KEY}=${payload.access_token}; path=/; samesite=lax`;
}

export function clearAuth(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  document.cookie = `${ACCESS_TOKEN_KEY}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; samesite=lax`;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(apiUrl('/api/v1/auth/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Přihlášení selhalo');
  }
  const payload = (await response.json()) as LoginResponse;
  storeAuth(payload);
  return payload;
}

export async function logout(): Promise<void> {
  const refreshToken = getStoredRefreshToken();
  if (refreshToken) {
    await fetch(apiUrl('/api/v1/auth/logout'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => undefined);
  }
  clearAuth();
}

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;

  const response = await fetch(apiUrl('/api/v1/auth/refresh'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearAuth();
    return null;
  }

  const payload = (await response.json()) as { access_token: string };
  localStorage.setItem(ACCESS_TOKEN_KEY, payload.access_token);
  document.cookie = `${ACCESS_TOKEN_KEY}=${payload.access_token}; path=/; samesite=lax`;
  return payload.access_token;
}

export async function authFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const token = getStoredAccessToken();
  const headers = new Headers(init.headers ?? {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response = await fetch(apiUrl(input), { ...init, headers });
  if (response.status !== 401) {
    return response;
  }

  const refreshedToken = await refreshAccessToken();
  if (!refreshedToken) {
    return response;
  }

  headers.set('Authorization', `Bearer ${refreshedToken}`);
  response = await fetch(apiUrl(input), { ...init, headers });
  return response;
}
