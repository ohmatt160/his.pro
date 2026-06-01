export type AuthUser = {
  facilitySlug: string;
  loginId: string;
  role: string;
  fullName: string;
  email?: string;
};

const TOKEN_STORAGE_KEY = "hispro.auth.token";
const USER_STORAGE_KEY = "hispro.auth.user";

const getApiBaseUrl = () => {
  const configuredUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "");
  if (configuredUrl) {
    return configuredUrl;
  }

  if (import.meta.env.PROD) {
    throw new Error(
      "VITE_API_BASE_URL is required in production. Set it to your backend /api/v1 URL."
    );
  }

  return "/api/v1";
};

type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export const getToken = () => {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
};

export const setToken = (token: string) => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
};

export const clearToken = () => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
};

export const getUser = (): AuthUser | null => {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    window.localStorage.removeItem(USER_STORAGE_KEY);
    return null;
  }
};

export const setUser = (user: AuthUser) => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
};

export const clearUser = () => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(USER_STORAGE_KEY);
};

const toHeaders = (headers?: HeadersInit) => {
  const normalized = new Headers(headers);

  const token = getToken();
  if (token) {
    normalized.set("Authorization", `Bearer ${token}`);
  }

  return normalized;
};

const buildUrl = (path: string) => {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  const baseUrl = getApiBaseUrl();
  const normalizedPath = path.startsWith("/") ? path.substring(1) : path;
  return baseUrl ? `${baseUrl}/${normalizedPath}` : `/${normalizedPath}`;
};

const parseErrorMessage = async (response: Response) => {
  const fallback = response.statusText || "API request failed";
  const text = await response.text();

  if (!text) {
    return fallback;
  }

  try {
    const payload = JSON.parse(text) as {
      detail?: unknown;
      error?: unknown;
      message?: unknown;
    };

    const message = payload.detail || payload.error || payload.message;
    if (typeof message === "string") {
      return message;
    }

    if (message) {
      return JSON.stringify(message);
    }

    return text;
  } catch {
    return text;
  }
};

const parseResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  const body = await response.text();
  if (!body) {
    return undefined as unknown as T;
  }

  try {
    return JSON.parse(body) as T;
  } catch {
    throw new Error("API response was not valid JSON");
  }
};

const isJsonBody = (body: unknown) =>
  body !== undefined &&
  body !== null &&
  typeof body !== "string" &&
  !(typeof FormData !== "undefined" && body instanceof FormData) &&
  !(typeof Blob !== "undefined" && body instanceof Blob) &&
  !(typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams) &&
  !(typeof ArrayBuffer !== "undefined" && body instanceof ArrayBuffer);

const prepareRequest = (options: ApiRequestOptions) => {
  const headers = toHeaders(options.headers);
  const body = options.body;

  if (isJsonBody(body)) {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    return {
      headers,
      body: JSON.stringify(body),
    };
  }

  return {
    headers,
    body: body as BodyInit | null | undefined,
  };
};

export const request = async <T>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<T> => {
  const url = buildUrl(path);
  const { headers, body } = prepareRequest(options);
  const { body: _body, ...fetchOptions } = options;
  const response = await fetch(url, {
    ...fetchOptions,
    headers,
    body,
  });

  return parseResponse<T>(response);
};

export const get = async <T>(path: string) => request<T>(path, { method: "GET" });
export const post = async <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body });
export const put = async <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "PUT", body });
export const del = async <T>(path: string) =>
  request<T>(path, { method: "DELETE" });

export const apiClient = {
  getToken,
  setToken,
  clearToken,
  getUser,
  setUser,
  clearUser,
  get,
  post,
  put,
  del,
  request,
  isSignedIn: () => Boolean(getToken()),
};
