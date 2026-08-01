import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import handler from "../api/tenant-redirect.js";

const vercelConfig = JSON.parse(
  readFileSync(new URL("../vercel.json", import.meta.url), "utf8")
);

const makeResponse = () => ({
  body: undefined,
  headers: new Map(),
  statusCode: 200,
  setHeader(name, value) {
    this.headers.set(name.toLowerCase(), value);
  },
  status(statusCode) {
    this.statusCode = statusCode;
    return this;
  },
  json(body) {
    this.body = body;
  },
  end(body) {
    this.body = body;
  },
});

const request = (query, host = "his-pro.vercel.app") => ({
  method: "GET",
  headers: { host },
  query,
});

const facilityResponse = (overrides = {}) =>
  new Response(
    JSON.stringify({
      slug: "sunrise-medical",
      canonical_subdomain: "sunrise-medical",
      ...overrides,
    }),
    { status: 200, headers: { "content-type": "application/json" } }
  );

test.beforeEach(() => {
  process.env.HF_BACKEND_URL = "https://backend.example.test";
  process.env.HF_TOKEN = "private-hf-token";
  process.env.TENANT_BASE_DOMAIN = "his-pro.vercel.app";
  process.env.PUBLIC_APP_ORIGIN = "https://his-pro.vercel.app";
  delete process.env.VERCEL_PROJECT_PRODUCTION_URL;
  delete process.env.VERCEL_URL;
});

test("does not send every canonical tenant hostname through a legacy redirect", () => {
  const catchAllTenantRedirects = vercelConfig.rewrites.filter(
    (rewrite) =>
      rewrite.source === "/:rest*" &&
      rewrite.destination.includes("/api/tenant-redirect")
  );
  assert.deepEqual(catchAllTenantRedirects, []);
});

test("validates a legacy facility and returns a configured-domain 308", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    assert.equal(
      url,
      "https://backend.example.test/api/v1/facilities/resolve-workspace/sunrise-medical"
    );
    assert.equal(options.headers.authorization, "Bearer private-hf-token");
    assert.equal(options.headers["x-forwarded-host"], "his-pro.vercel.app");
    return facilityResponse();
  };

  try {
    const response = makeResponse();
    await handler(
      request(
        {
          __hispro_facility: "sunrise-medical",
          __hispro_kind: "dashboard",
          __hispro_rest: "patients/patient-1/timeline",
          tab: "history",
        },
        "attacker.example.test"
      ),
      response
    );

    assert.equal(response.statusCode, 308);
    assert.equal(
      response.headers.get("location"),
      "https://sunrise-medical.his-pro.vercel.app/dashboard/patients/patient-1/timeline?tab=history"
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("normalizes path-based branch URLs from an old tenant hostname", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => facilityResponse();

  try {
    const response = makeResponse();
    await handler(
      request({
        __hispro_facility: "sunrise-medical",
        __hispro_kind: "preserve",
        __hispro_rest: "sunrise-medical/branches/lagos/dashboard/laboratory",
      }),
      response
    );

    assert.equal(response.statusCode, 308);
    assert.equal(
      response.headers.get("location"),
      "https://sunrise-medical.his-pro.vercel.app/branches/lagos/dashboard/laboratory"
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("keeps long path-safe branch slugs during migration", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => facilityResponse();
  const branchSlug = `branch-${"a".repeat(80)}`;

  try {
    const response = makeResponse();
    await handler(
      request({
        __hispro_facility: "sunrise-medical",
        __hispro_kind: "branch",
        __hispro_branch: branchSlug,
        __hispro_rest: "dashboard",
      }),
      response
    );

    assert.equal(response.statusCode, 308);
    assert.equal(
      response.headers.get("location"),
      `https://sunrise-medical.his-pro.vercel.app/branches/${branchSlug}/dashboard`
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects malformed encoded legacy paths without caching a redirect", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => facilityResponse();

  try {
    const response = makeResponse();
    await handler(
      request({
        __hispro_facility: "sunrise-medical",
        __hispro_kind: "preserve",
        __hispro_rest: "%E0%A4%A",
      }),
      response
    );

    assert.equal(response.statusCode, 400);
    assert.equal(response.headers.get("location"), undefined);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects an upstream tenant identity mismatch", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => facilityResponse({ slug: "another-facility" });

  try {
    const response = makeResponse();
    await handler(
      request({
        __hispro_facility: "sunrise-medical",
        __hispro_kind: "login",
      }),
      response
    );

    assert.equal(response.statusCode, 502);
    assert.equal(response.headers.get("location"), undefined);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("does not permanently cache an unknown legacy workspace", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response("", { status: 404 });

  try {
    const response = makeResponse();
    await handler(
      request({
        __hispro_facility: "missing-clinic",
        __hispro_kind: "login",
      }),
      response
    );

    assert.equal(response.statusCode, 307);
    assert.equal(
      response.headers.get("location"),
      "https://his-pro.vercel.app/login?workspace=missing-clinic"
    );
    assert.equal(response.headers.get("cache-control"), "private, no-store");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("supports a custom wildcard tenant domain without code changes", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => facilityResponse();
  process.env.TENANT_BASE_DOMAIN = "his.pro";

  try {
    const response = makeResponse();
    await handler(
      request({
        __hispro_facility: "sunrise-medical",
        __hispro_kind: "login",
      }),
      response
    );

    assert.equal(response.statusCode, 308);
    assert.equal(
      response.headers.get("location"),
      "https://sunrise-medical.his.pro/login"
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("fails closed when the configured tenant domain contains URL syntax", async () => {
  const originalFetch = globalThis.fetch;
  let fetched = false;
  globalThis.fetch = async () => {
    fetched = true;
    return facilityResponse();
  };
  process.env.TENANT_BASE_DOMAIN = "his-pro.vercel.app/attacker";

  try {
    const response = makeResponse();
    await handler(
      request({
        __hispro_facility: "sunrise-medical",
        __hispro_kind: "login",
      }),
      response
    );

    assert.equal(response.statusCode, 503);
    assert.equal(response.headers.get("location"), undefined);
    assert.equal(fetched, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
