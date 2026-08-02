export const config = {
  api: {
    bodyParser: false,
  },
};

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "accept-language",
  "content-type",
  "cookie",
  "idempotency-key",
  "user-agent",
  "x-csrf-token",
  "x-forwarded-for",
  "x-onboarding-token",
];

const readBody = async (request) => {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return chunks.length ? Buffer.concat(chunks) : undefined;
};

const asArray = (value) => {
  if (!value) {
    return [];
  }
  return Array.isArray(value) ? value : [value];
};

const splitSetCookie = (value) => {
  if (!value) {
    return [];
  }
  return value.split(/,(?=\s*[^;,=\s]+=[^;])/g).map((item) => item.trim());
};

const getSetCookieHeaders = (headers) => {
  const values =
    typeof headers.getSetCookie === "function"
      ? headers.getSetCookie()
      : [headers.get("set-cookie")];

  return values.flatMap(splitSetCookie);
};

export default async function handler(request, response) {
  const backendUrl = process.env.HF_BACKEND_URL?.trim().replace(/\/+$/, "");
  const hfToken = process.env.HF_TOKEN || process.env.HUGGINGFACE_TOKEN;

  if (!backendUrl || !hfToken) {
    console.error("HIS.Pro proxy configuration is incomplete", {
      hasBackendUrl: Boolean(backendUrl),
      hasHfToken: Boolean(hfToken),
    });
    response.status(500).json({
      message: "Backend proxy is not configured.",
      code: "PROXY_NOT_CONFIGURED",
      status: 500,
    });
    return;
  }

  const path = asArray(request.query.path).join("/");
  const target = new URL(`${backendUrl}/api/v1/${path}`);
  for (const [key, value] of Object.entries(request.query)) {
    if (key === "path") {
      continue;
    }
    for (const entry of asArray(value)) {
      target.searchParams.append(key, entry);
    }
  }

  const headers = new Headers();
  for (const key of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers[key];
    if (value) {
      headers.set(key, Array.isArray(value) ? value.join(", ") : value);
    }
  }

  if (request.headers.authorization) {
    headers.set(
      "x-hispro-authorization",
      Array.isArray(request.headers.authorization)
        ? request.headers.authorization[0]
        : request.headers.authorization
    );
  }
  headers.set("authorization", `Bearer ${hfToken}`);
  headers.set("x-forwarded-host", request.headers.host || "");
  headers.set("x-forwarded-proto", "https");

  const body = ["GET", "HEAD"].includes(request.method || "")
    ? undefined
    : await readBody(request);

  try {
    const backendResponse = await fetch(target, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
    });

    const responseBody = Buffer.from(await backendResponse.arrayBuffer());
    const contentType = backendResponse.headers.get("content-type") || "";

    if (backendResponse.status >= 500 && contentType.includes("text/html")) {
      console.error("HIS.Pro upstream returned HTML error", {
        method: request.method,
        path,
        status: backendResponse.status,
      });
      response.status(backendResponse.status).json({
        message: "Backend request failed. Please try again.",
        code: "UPSTREAM_ERROR",
        status: backendResponse.status,
      });
      return;
    }

    response.status(backendResponse.status);
    backendResponse.headers.forEach((value, key) => {
      const lowerKey = key.toLowerCase();
      if (
        HOP_BY_HOP_HEADERS.has(lowerKey) ||
        lowerKey.startsWith("access-control-") ||
        lowerKey === "set-cookie"
      ) {
        return;
      }
      response.setHeader(key, value);
    });
    const setCookieHeaders = getSetCookieHeaders(backendResponse.headers);
    if (setCookieHeaders.length) {
      response.setHeader("set-cookie", setCookieHeaders);
    }
    const isPublicTenantResolution =
      request.method === "GET" &&
      /^facilities\/resolve-host\/[a-z0-9-]+$/.test(path) &&
      !backendResponse.headers.get("set-cookie");
    response.setHeader(
      "cache-control",
      isPublicTenantResolution
        ? backendResponse.headers.get("cache-control") ||
            "public, max-age=60, s-maxage=300, stale-while-revalidate=60"
        : "no-store"
    );
    response.end(responseBody);
  } catch (error) {
    console.error("HIS.Pro proxy failed", {
      method: request.method,
      path,
      message: error instanceof Error ? error.message : String(error),
    });
    response.status(502).json({
      message: "Backend is temporarily unavailable. Please try again.",
      code: "PROXY_ERROR",
      status: 502,
    });
  }
}
