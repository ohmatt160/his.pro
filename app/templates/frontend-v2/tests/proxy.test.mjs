import assert from "node:assert/strict";
import test from "node:test";

import handler, { config } from "../api/proxy.js";
import legacyHandler, { config as legacyConfig } from "../api/v1/[...path].js";

const makeRequest = ({ method = "POST", headers = {}, path = ["auth", "refresh"], body } = {}) => ({
  method,
  headers,
  query: { path },
  async *[Symbol.asyncIterator]() {
    if (body !== undefined) {
      yield Buffer.from(body);
    }
  },
});

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

test.beforeEach(() => {
  process.env.HF_BACKEND_URL = "https://backend.example.test";
  process.env.HF_TOKEN = "private-service-token";
});

test("uses the hardened proxy for the filesystem API route", () => {
  assert.equal(legacyHandler, handler);
  assert.equal(legacyConfig, config);
});

test("forwards CSRF, idempotency, onboarding, cookies, and user authorization safely", async () => {
  const originalFetch = globalThis.fetch;
  let upstreamRequest;
  globalThis.fetch = async (url, options) => {
    upstreamRequest = { url: String(url), options };
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const response = makeResponse();
    await handler(
      makeRequest({
        headers: {
          accept: "application/json",
          authorization: "Bearer user-access-token",
          cookie: "hispro_refresh_token=refresh; hispro_csrf_token=csrf-token",
          host: "his-pro.vercel.app",
          "idempotency-key": "write-once-123",
          "x-csrf-token": "csrf-token",
          "x-not-allowed": "must-not-cross-proxy",
          "x-onboarding-token": "onboarding-secret",
        },
      }),
      response
    );

    assert.equal(response.statusCode, 200);
    assert.equal(upstreamRequest.url, "https://backend.example.test/api/v1/auth/refresh");
    const headers = upstreamRequest.options.headers;
    assert.equal(headers.get("authorization"), "Bearer private-service-token");
    assert.equal(headers.get("x-hispro-authorization"), "Bearer user-access-token");
    assert.equal(headers.get("x-csrf-token"), "csrf-token");
    assert.equal(headers.get("idempotency-key"), "write-once-123");
    assert.equal(headers.get("x-onboarding-token"), "onboarding-secret");
    assert.equal(
      headers.get("cookie"),
      "hispro_refresh_token=refresh; hispro_csrf_token=csrf-token"
    );
    assert.equal(headers.has("x-not-allowed"), false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("preserves all rotated authentication cookies from the backend", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ access_token: "access" }), {
      status: 200,
      headers: {
        "content-type": "application/json",
        "set-cookie": [
          "hispro_access_token=access; Path=/; HttpOnly; Secure; SameSite=None",
          "hispro_refresh_token=refresh; Path=/; HttpOnly; Secure; SameSite=None",
          "hispro_csrf_token=csrf; Path=/; Secure; SameSite=None",
        ].join(", "),
      },
    });

  try {
    const response = makeResponse();
    await handler(
      makeRequest({
        headers: { host: "his-pro.vercel.app" },
      }),
      response
    );

    const cookies = response.headers.get("set-cookie");
    assert.equal(cookies.length, 3);
    assert.match(cookies[0], /^hispro_access_token=/);
    assert.match(cookies[1], /^hispro_refresh_token=/);
    assert.match(cookies[2], /^hispro_csrf_token=/);
    assert.equal(response.headers.get("cache-control"), "no-store");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
