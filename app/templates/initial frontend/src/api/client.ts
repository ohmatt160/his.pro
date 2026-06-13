export type AuthUser = {
  id?: string;
  facilityId?: string;
  facilitySlug: string;
  loginId: string;
  role: string;
  fullName: string;
  email?: string;
};

const USER_STORAGE_KEY = "hispro.auth.user";
export const AUTH_EXPIRED_EVENT = "hispro:auth-expired";
let inMemoryAuthToken: string | null = null;
let refreshRequest: Promise<string | null> | null = null;

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
  authToken?: string | null;
};

export const getToken = () => {
  return inMemoryAuthToken;
};

export const setToken = (token: string) => {
  inMemoryAuthToken = token;
};

export const clearToken = () => {
  inMemoryAuthToken = null;
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

const notifyAuthExpired = () => {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
  }
};

const toHeaders = (headers?: HeadersInit, authToken?: string | null) => {
  const normalized = new Headers(headers);

  const token = authToken === undefined ? getToken() : authToken;
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

    const rawError =
      payload.error && typeof payload.error === "object"
        ? (payload.error as { message?: unknown; details?: unknown })
        : null;
    const message =
      payload.detail ||
      rawError?.message ||
      payload.error ||
      payload.message;
    const details = rawError?.details;

    if (Array.isArray(details)) {
      const firstDetail = details[0] as { loc?: unknown[]; msg?: unknown } | undefined;
      const field = firstDetail?.loc?.at(-1);
      if (typeof firstDetail?.msg === "string" && typeof field === "string") {
        return `${field.replaceAll("_", " ")}: ${firstDetail.msg}`;
      }
      return "Please check the form and try again.";
    }

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

const isAuthRefreshable = (path: string, options: ApiRequestOptions) =>
  options.authToken === undefined &&
  !path.includes("/auth/login") &&
  !path.includes("/auth/register") &&
  !path.includes("/auth/ensure") &&
  !path.includes("/auth/refresh") &&
  !path.includes("/auth/logout");

const refreshAccessToken = async () => {
  if (!refreshRequest) {
    refreshRequest = fetch(buildUrl("/auth/refresh"), {
      method: "POST",
      credentials: "include",
    })
      .then(async (response) => {
        if (!response.ok) {
          clearToken();
          clearUser();
          notifyAuthExpired();
          return null;
        }

        const refreshed = (await parseResponse<{
          access_token: string;
          refresh_token: string;
          token_type: "bearer";
        }>(response)) as { access_token: string };
        setToken(refreshed.access_token);
        return refreshed.access_token;
      })
      .catch(() => {
        clearToken();
        clearUser();
        notifyAuthExpired();
        return null;
      })
      .finally(() => {
        refreshRequest = null;
      });
  }

  return refreshRequest;
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
  const headers = toHeaders(options.headers, options.authToken);
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
  const { authToken: _authToken, body: _body, ...fetchOptions } = options;
  let response = await fetch(url, {
    ...fetchOptions,
    headers,
    body,
    credentials: fetchOptions.credentials ?? "include",
  });

  if (response.status === 401 && isAuthRefreshable(path, options)) {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      const retryHeaders = toHeaders(options.headers, refreshedToken);
      response = await fetch(url, {
        ...fetchOptions,
        headers: retryHeaders,
        body,
        credentials: fetchOptions.credentials ?? "include",
      });
    } else {
      notifyAuthExpired();
    }
  }

  return parseResponse<T>(response);
};

export const get = async <T>(path: string) => request<T>(path, { method: "GET" });
export const post = async <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body });
export const put = async <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "PUT", body });
export const del = async <T>(path: string) =>
  request<T>(path, { method: "DELETE" });
export const downloadBlob = async (path: string) => {
  const url = buildUrl(path);
  const response = await fetch(url, {
    method: "GET",
    headers: toHeaders(),
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return response.blob();
};

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
  downloadBlob,
  request,
  isSignedIn: () => Boolean(getToken()),
};
