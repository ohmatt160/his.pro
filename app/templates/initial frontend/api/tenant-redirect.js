const FACILITY_SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?$/;
const SUBDOMAIN_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;
const PATH_SEGMENT_PATTERN = /^[a-zA-Z0-9._~-]+$/;
const MAX_PATH_SEGMENT_LENGTH = 200;
const TENANT_BASE_DOMAIN = "app.his.pro";
const INTERNAL_QUERY_PREFIX = "__hispro_";

const firstValue = (value) => (Array.isArray(value) ? value[0] : value || "");

const decodePathSegment = (value) => {
  try {
    const decoded = decodeURIComponent(String(value));
    if (
      !decoded ||
      decoded.length > MAX_PATH_SEGMENT_LENGTH ||
      !PATH_SEGMENT_PATTERN.test(decoded)
    ) {
      return null;
    }
    return decoded;
  } catch {
    return null;
  }
};

const safeSegments = (value) => {
  const raw = String(firstValue(value)).replace(/^\/+|\/+$/g, "");
  if (!raw) {
    return [];
  }

  const segments = raw.split("/").map(decodePathSegment);
  if (segments.some((segment) => segment === null)) {
    return null;
  }
  return segments.map(encodeURIComponent);
};

const canonicalizePreservedPath = (segments, facilitySlug) => {
  if (!segments?.length) {
    return "/login";
  }

  const decoded = segments.map(decodeURIComponent);
  if (
    (decoded.length === 1 && decoded[0] === facilitySlug) ||
    (decoded.length === 2 && decoded[0] === facilitySlug && decoded[1] === "login") ||
    (decoded.length === 2 && decoded[0] === "login" && decoded[1] === facilitySlug)
  ) {
    return "/login";
  }
  if (decoded[0] === "dashboard" && decoded[1] === facilitySlug) {
    return `/${["dashboard", ...segments.slice(2)].join("/")}`;
  }
  if (decoded[0] === "portal" && decoded[1] === facilitySlug) {
    return "/portal";
  }
  if (decoded[0] === facilitySlug && decoded[1] === "branches" && decoded[2]) {
    return `/${["branches", ...segments.slice(2)].join("/")}`;
  }
  if (decoded[0] === "workspace-ready" && decoded[1] === facilitySlug) {
    return "/workspace-ready";
  }
  if (decoded[0] === "hospital" && decoded[1] === facilitySlug) {
    return "/hospital";
  }

  return `/${segments.join("/")}`;
};

const buildTargetPath = (kind, query, facilitySlug) => {
  const rest = safeSegments(query.__hispro_rest);
  if (rest === null) {
    return null;
  }

  switch (kind) {
    case "login":
      return "/login";
    case "dashboard":
      return `/${["dashboard", ...rest].join("/")}`;
    case "portal":
      return "/portal";
    case "branch": {
      const branch = decodePathSegment(firstValue(query.__hispro_branch));
      if (!branch) {
        return null;
      }
      return `/${["branches", encodeURIComponent(branch), ...rest].join("/")}`;
    }
    case "workspace-ready":
      return "/workspace-ready";
    case "hospital":
      return "/hospital";
    case "preserve":
      return canonicalizePreservedPath(rest, facilitySlug);
    default:
      return null;
  }
};

const appendOriginalQuery = (url, query) => {
  for (const [key, rawValue] of Object.entries(query)) {
    if (key.startsWith(INTERNAL_QUERY_PREFIX)) {
      continue;
    }
    for (const value of Array.isArray(rawValue) ? rawValue : [rawValue]) {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    }
  }
};

const redirect = (response, status, location, cacheControl) => {
  response.statusCode = status;
  response.setHeader("Location", location);
  response.setHeader("Cache-Control", cacheControl);
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.end();
};

export default async function handler(request, response) {
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.setHeader("Allow", "GET, HEAD");
    response.status(405).json({ message: "Method not allowed." });
    return;
  }

  const backendUrl = process.env.HF_BACKEND_URL?.trim().replace(/\/+$/, "");
  const hfToken = process.env.HF_TOKEN || process.env.HUGGINGFACE_TOKEN;
  if (!backendUrl || !hfToken) {
    response.status(503).json({ message: "Tenant routing is temporarily unavailable." });
    return;
  }

  const facilitySlug = firstValue(request.query.__hispro_facility).toLowerCase();
  const kind = firstValue(request.query.__hispro_kind);
  if (!FACILITY_SLUG_PATTERN.test(facilitySlug)) {
    redirect(
      response,
      307,
      "https://his.pro/login",
      "private, no-store"
    );
    return;
  }

  try {
    const upstream = await fetch(
      `${backendUrl}/api/v1/facilities/resolve-workspace/${encodeURIComponent(facilitySlug)}`,
      {
        method: "GET",
        headers: {
          accept: "application/json",
          authorization: `Bearer ${hfToken}`,
          "x-forwarded-host": request.headers.host || "",
          "x-forwarded-proto": "https",
        },
        redirect: "manual",
        signal: AbortSignal.timeout(5_000),
      }
    );

    if (upstream.status === 404) {
      const fallback = new URL("https://his.pro/login");
      fallback.searchParams.set("workspace", facilitySlug);
      redirect(response, 307, fallback.toString(), "private, no-store");
      return;
    }
    if (!upstream.ok) {
      response.status(503).json({ message: "Tenant routing is temporarily unavailable." });
      return;
    }

    const facility = await upstream.json();
    const canonicalSubdomain = String(facility.canonical_subdomain || "").toLowerCase();
    if (
      facility.slug !== facilitySlug ||
      !SUBDOMAIN_PATTERN.test(canonicalSubdomain)
    ) {
      response.status(502).json({ message: "Tenant routing response was invalid." });
      return;
    }

    const targetPath = buildTargetPath(kind, request.query, facilitySlug);
    if (!targetPath) {
      response.status(400).json({ message: "Legacy workspace URL is invalid." });
      return;
    }

    const destination = new URL(
      targetPath,
      `https://${canonicalSubdomain}.${TENANT_BASE_DOMAIN}`
    );
    appendOriginalQuery(destination, request.query);
    redirect(
      response,
      308,
      destination.toString(),
      "public, max-age=3600, s-maxage=86400, immutable"
    );
  } catch {
    response.status(503).json({ message: "Tenant routing is temporarily unavailable." });
  }
}
