const DEFAULT_TENANT_BASE_DOMAIN = "app.his.pro";
const DNS_LABEL_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;
const RESERVED_SUBDOMAINS = new Set([
  "admin",
  "api",
  "app",
  "assets",
  "auth",
  "cdn",
  "help",
  "mail",
  "static",
  "status",
  "support",
  "www",
]);

const normalizeHostname = (hostname: string) =>
  hostname.trim().toLowerCase().replace(/\.$/, "");

export const getTenantBaseDomain = () =>
  normalizeHostname(
    import.meta.env.VITE_TENANT_BASE_DOMAIN || DEFAULT_TENANT_BASE_DOMAIN
  );

export const isValidCanonicalSubdomain = (value: string) =>
  DNS_LABEL_PATTERN.test(value.trim().toLowerCase()) &&
  !RESERVED_SUBDOMAINS.has(value.trim().toLowerCase());

export const getCanonicalSubdomainFromHostname = (
  hostname = typeof window !== "undefined" ? window.location.hostname : "",
  baseDomain = getTenantBaseDomain()
) => {
  const normalizedHostname = normalizeHostname(hostname);
  const normalizedBaseDomain = normalizeHostname(baseDomain);
  const suffix = `.${normalizedBaseDomain}`;

  if (!normalizedHostname.endsWith(suffix)) {
    return "";
  }

  const subdomain = normalizedHostname.slice(0, -suffix.length);
  return isValidCanonicalSubdomain(subdomain) ? subdomain : "";
};

export const isCanonicalTenantHost = () =>
  Boolean(getCanonicalSubdomainFromHostname());

export const getCanonicalTenantOrigin = (canonicalSubdomain: string) => {
  const normalized = canonicalSubdomain.trim().toLowerCase();
  if (!isValidCanonicalSubdomain(normalized)) {
    throw new Error("A valid facility subdomain is required.");
  }

  return `https://${normalized}.${getTenantBaseDomain()}`;
};

export const getCanonicalTenantUrl = (
  canonicalSubdomain: string,
  path = "/login"
) => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getCanonicalTenantOrigin(canonicalSubdomain)}${normalizedPath}`;
};

export const getTenantPath = (canonicalPath: string, legacyPath: string) =>
  isCanonicalTenantHost() ? canonicalPath : legacyPath;

export const getCurrentBranchSlugFromPath = (facilitySlug: string) => {
  if (typeof window === "undefined") {
    return "";
  }

  const canonicalMatch = window.location.pathname.match(
    /^\/branches\/([^/]+)(?:\/|$)/
  );
  if (canonicalMatch) {
    return canonicalMatch[1];
  }

  if (!facilitySlug) {
    return "";
  }
  const escapedFacilitySlug = facilitySlug.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const legacyMatch = window.location.pathname.match(
    new RegExp(`^/${escapedFacilitySlug}/branches/([^/]+)(?:/|$)`)
  );
  return legacyMatch?.[1] || "";
};

export const getCanonicalPathForLegacyPath = (
  pathname: string,
  facilitySlug: string
) => {
  if (!facilitySlug) {
    return pathname;
  }

  const escapedSlug = facilitySlug.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const rules: Array<[RegExp, (match: RegExpMatchArray) => string]> = [
    [new RegExp(`^/login/${escapedSlug}/?$`), () => "/login"],
    [new RegExp(`^/${escapedSlug}(?:/login)?/?$`), () => "/login"],
    [
      new RegExp(`^/dashboard/${escapedSlug}(?<rest>/.*)?$`),
      (match) => `/dashboard${match.groups?.rest || ""}`,
    ],
    [new RegExp(`^/portal/${escapedSlug}/?$`), () => "/portal"],
    [
      new RegExp(`^/${escapedSlug}/branches/(?<branch>[^/]+)(?<rest>/.*)?$`),
      (match) => `/branches/${match.groups?.branch}${match.groups?.rest || ""}`,
    ],
    [new RegExp(`^/workspace-ready/${escapedSlug}/?$`), () => "/workspace-ready"],
    [new RegExp(`^/hospital/${escapedSlug}/?$`), () => "/hospital"],
  ];

  for (const [pattern, destination] of rules) {
    const match = pathname.match(pattern);
    if (match) {
      return destination(match);
    }
  }

  return pathname;
};
