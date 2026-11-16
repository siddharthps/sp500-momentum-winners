// Starts the monthly run (#76). Each night it (1) makes sure monthly.yml is enabled, since GitHub
// disables workflows in public repositories after 60 days without repository activity, and
// (2) dispatches it, asking for a real run (dry_run=false) that respects the `due` check, so on
// most days the workflow stops after reading the running record.

const API = "https://api.github.com";

function headers(env) {
  return {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${env.GITHUB_TOKEN}`,
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "sp500-momentum-monthly-trigger",
    "Content-Type": "application/json",
  };
}

export function enableRequest(env) {
  const url = `${API}/repos/${env.REPO}/actions/workflows/${env.WORKFLOW}/enable`;
  return { url, init: { method: "PUT", headers: headers(env) } };
}

export function dispatchRequest(env) {
  const url = `${API}/repos/${env.REPO}/actions/workflows/${env.WORKFLOW}/dispatches`;
  const init = {
    method: "POST",
    headers: headers(env),
    body: JSON.stringify({
      ref: "main",
      inputs: { dry_run: "false", force: "false", respect_due: "true" },
    }),
  };
  return { url, init };
}

async function call(what, { url, init }, fetchImpl) {
  const response = await fetchImpl(url, init);
  if (response.status !== 204) {
    // GitHub's error body says what's wrong (expired token, missing permission); it never
    // contains the token itself.
    const detail = (await response.text()).slice(0, 300);
    throw new Error(`GitHub ${what} failed: HTTP ${response.status} ${detail}`);
  }
  return response.status;
}

export async function trigger(env, fetchImpl = fetch) {
  await call("enable", enableRequest(env), fetchImpl);
  return call("dispatch", dispatchRequest(env), fetchImpl);
}

export default {
  async scheduled(controller, env, ctx) {
    await trigger(env); // a thrown error marks this cron run as failed in Cloudflare
    console.log(`Enabled and dispatched ${env.WORKFLOW} (cron ${controller.cron})`);
  },
};
