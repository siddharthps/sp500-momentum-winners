import assert from "node:assert/strict";
import { test } from "node:test";

import { dispatchRequest, enableRequest, trigger } from "../src/index.js";

const env = { REPO: "owner/repo", WORKFLOW: "monthly.yml", GITHUB_TOKEN: "t0ken" };
const base = "https://api.github.com/repos/owner/repo/actions/workflows/monthly.yml";

test("dispatches a real run that respects the due check", () => {
  const { url, init } = dispatchRequest(env);
  assert.equal(url, `${base}/dispatches`);
  assert.equal(init.method, "POST");
  assert.equal(init.headers.Authorization, "Bearer t0ken");
  assert.deepEqual(JSON.parse(init.body), {
    ref: "main",
    inputs: { dry_run: "false", force: "false", respect_due: "true" },
  });
});

test("re-enables the workflow first (GitHub's 60-day rule)", async () => {
  assert.deepEqual(enableRequest(env).url, `${base}/enable`);
  assert.equal(enableRequest(env).init.method, "PUT");
  const calls = [];
  const fake = async (url) => {
    calls.push(url);
    return { status: 204, text: async () => "" };
  };
  assert.equal(await trigger(env, fake), 204);
  assert.deepEqual(calls, [`${base}/enable`, `${base}/dispatches`]);
});

test("anything but 204 fails loudly, without the token in the message", async () => {
  const fake = async () => ({ status: 401, text: async () => '{"message":"Bad credentials"}' });
  await assert.rejects(trigger(env, fake), (e) => {
    assert.match(e.message, /enable failed: HTTP 401/);
    assert.doesNotMatch(e.message, /t0ken/);
    return true;
  });
});
