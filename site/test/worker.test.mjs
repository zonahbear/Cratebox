// node site/test/worker.test.mjs: runs the signup → approve → invite → TestFlight flow against fake
// App Store Connect, Resend and KV. Prints PASS/FAIL lines like the repo's other tests.
import worker, { _test } from "../src/worker.js";

let fails = 0;
const check = (name, cond, extra = "") => { console.log(`${cond ? "PASS" : "FAIL"} ${name}${cond ? "" : " " + extra}`); if (!cond) fails++; };

// In-memory KV with list() metadata, like Workers KV.
function kv() {
  const m = new Map();
  return {
    m,
    async get(k, type) { const v = m.get(k); return v == null ? null : type === "json" ? JSON.parse(v.value) : v.value; },
    async put(k, value, o = {}) { m.set(k, { value, metadata: o.metadata }); },
    async delete(k) { m.delete(k); },
    async list({ prefix }) { return { keys: [...m].filter(([k]) => k.startsWith(prefix)).map(([name, v]) => ({ name, metadata: v.metadata })), list_complete: true }; },
  };
}

// A real P-256 key in .p8 (PKCS#8 PEM) form, so the JWT path is exercised for real.
const kp = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
const p8 = "-----BEGIN PRIVATE KEY-----\n" + Buffer.from(await crypto.subtle.exportKey("pkcs8", kp.privateKey)).toString("base64") + "\n-----END PRIVATE KEY-----";

const env = {
  DB: kv(), ASSETS: { fetch: async () => new Response("asset") },
  ASC_KEY_ID: "KEY123", ASC_ISSUER_ID: "issuer-uuid", ASC_KEY_P8: p8, RESEND_API_KEY: "re_test", ADMIN_EMAIL: "owner@example.com",
  LINK_SECRET: "test-secret", SITE_URL: "https://site.test", ASC_BUNDLE_ID: "com.zonahbear.cratebox.suite", ASC_GROUP_NAME: "", ASC_ROLE: "MARKETING", AUTO_APPROVE: "false",
};
const waits = [];
const ctx = { waitUntil: (p) => waits.push(p) };
const settle = async () => { while (waits.length) await waits.shift(); };

// Fake Apple + Resend.
const calls = [], mails = [];
let teamUsers = new Set(), testers = new Map();
globalThis.fetch = async (url, init = {}) => {
  url = String(url); const body = init.body ? JSON.parse(init.body) : null;
  if (url.startsWith("https://api.resend.com/")) { mails.push(body); return new Response("{}"); }
  calls.push({ method: init.method, url, body, auth: init.headers?.authorization });
  const u = new URL(url), p = u.pathname;
  const ok = (o, s = 200) => new Response(JSON.stringify(o), { status: s });
  if (p === "/v1/apps") return ok({ data: [{ id: "APP1" }] });
  if (p === "/v1/apps/APP1/betaGroups") return ok({ data: [{ id: "EXT", attributes: { name: "Public", isInternalGroup: false } }, { id: "GRP", attributes: { name: "Homies", isInternalGroup: true } }] });
  if (p === "/v1/users") return ok({ data: teamUsers.has(u.searchParams.get("filter[username]")) ? [{ id: "U1" }] : [] });
  if (p === "/v1/userInvitations") return ok({ data: { id: "INV1" } }, 201);
  if (p === "/v1/betaTesters" && init.method === "POST") {
    const e = body.data.attributes.email;
    if (testers.has(e)) return ok({ errors: [{ detail: "exists" }] }, 409);
    testers.set(e, body.data.relationships.betaGroups.data[0].id); return ok({ data: { id: "T1" } }, 201);
  }
  if (p === "/v1/betaTesters") return ok({ data: [{ id: "T9" }] });
  if (p.startsWith("/v1/betaGroups/")) return new Response(null, { status: 204 });
  return ok({ errors: [{ detail: "unexpected " + p }] }, 500);
};

const req = (path, o = {}) => new Request("https://site.test" + path, o);
const post = (path, data, ip = "1.2.3.4") => worker.fetch(req(path, { method: "POST", headers: { "content-type": "application/json", "cf-connecting-ip": ip }, body: JSON.stringify(data) }), env, ctx);
const sam = { first: "Sam", last: "Rivera", email: "Sam@Example.com ", consent: "on", website: "" };

// --- JWT ---
const jwt = await _test.ascToken(env);
const [h, c, s] = jwt.split(".");
const dec = (x) => JSON.parse(Buffer.from(x, "base64url").toString());
check("jwt header is ES256 with key id", dec(h).alg === "ES256" && dec(h).kid === "KEY123");
check("jwt claims audience/issuer/expiry ≤ 20 min", dec(c).aud === "appstoreconnect-v1" && dec(c).iss === "issuer-uuid" && dec(c).exp - dec(c).iat <= 1200);
check("jwt signature verifies with the public key", await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, kp.publicKey, Buffer.from(s, "base64url"), new TextEncoder().encode(h + "." + c)));

// --- signup validation ---
check("static paths go to assets", (await (await worker.fetch(req("/"), env, ctx)).text()) === "asset");
check("bad email rejected", (await post("/api/signup", { ...sam, email: "nope" })).status === 400);
check("missing consent rejected", (await post("/api/signup", { ...sam, consent: "" })).status === 400);
let r = await post("/api/signup", { ...sam, website: "spam.biz" });
check("honeypot answers ok but stores nothing", r.status === 200 && ![...env.DB.m.keys()].some((k) => k.startsWith("s:")));

// --- signup → owner email ---
r = await post("/api/signup", sam); await settle();
const id = await _test.idFor("sam@example.com");
let rec = await env.DB.get("s:" + id, "json");
check("signup stored as pending with normalised email", r.status === 200 && rec?.status === "pending" && rec.email === "sam@example.com");
check("owner gets one approval email", mails.length === 1 && mails[0].to[0] === "owner@example.com" && /Approve/.test(mails[0].html));
check("no Apple calls before approval", calls.filter((x) => x.url.includes("userInvitations")).length === 0);
const approve = mails[0].html.match(/href="([^"]+t=[^"]*approve[^"]*)"/)[1].replace(/&amp;/g, "&");
check("approval link points at the site", approve.startsWith("https://site.test/api/review?t="));
r = await post("/api/signup", sam); await settle();
check("repeat signup is quiet (no second email)", r.status === 200 && mails.length === 1);

// --- review link ---
const t = new URL(approve).searchParams.get("t");
r = await worker.fetch(req("/api/review?t=" + encodeURIComponent(t)), env, ctx);
let html = await r.text();
check("GET shows a confirm button and changes nothing", /<form method="post"/.test(html) && (await env.DB.get("s:" + id, "json")).status === "pending");
const forged = t.replace(".approve.", ".decline.");
r = await worker.fetch(req("/api/review?t=" + encodeURIComponent(forged)), env, ctx);
check("edited link is rejected", /not valid/.test(await r.text()));
const old = await _test.makeToken(env, id, "approve", Date.now() - 8 * 86400e3);
r = await worker.fetch(req("/api/review?t=" + encodeURIComponent(old)), env, ctx);
check("expired link is rejected", /expired/i.test(await r.text()));

r = await worker.fetch(req("/api/review", { method: "POST", body: new URLSearchParams({ t }) }), env, ctx);
html = await r.text();
const inv = calls.find((x) => x.url.endsWith("/v1/userInvitations"));
check("approve sends the team invite", /Approved/.test(html) && !!inv, html);
check("invite: MARKETING role, this app only, no provisioning",
  inv && inv.body.data.attributes.roles[0] === "MARKETING" && inv.body.data.attributes.allAppsVisible === false && inv.body.data.attributes.provisioningAllowed === false && inv.body.data.relationships.visibleApps.data[0].id === "APP1");
check("Apple calls carry a bearer JWT", inv && /^Bearer .+\..+\..+$/.test(inv.auth));
check("record is now invited", (await env.DB.get("s:" + id, "json")).status === "invited");
r = await worker.fetch(req("/api/review", { method: "POST", body: new URLSearchParams({ t }) }), env, ctx);
check("re-using the link does nothing twice", /Already handled/.test(await r.text()) && calls.filter((x) => x.url.endsWith("/v1/userInvitations")).length === 1);

// --- cron ---
await _test.sweep(env);
check("cron waits while the invite isn't accepted", (await env.DB.get("s:" + id, "json")).status === "invited" && !testers.size);
teamUsers.add("sam@example.com");
const mailsBefore = mails.length;
await _test.sweep(env);
check("cron adds accepted users to the INTERNAL group", testers.get("sam@example.com") === "GRP" && (await env.DB.get("s:" + id, "json")).status === "added");
check("owner told they're in", mails.length === mailsBefore + 1 && /is in TestFlight/.test(mails.at(-1).subject));

// --- already a team member: approve goes straight to the group, 409 path links the existing tester ---
teamUsers.add("pat@example.com"); testers.set("pat@example.com", "OTHER");
await post("/api/signup", { ...sam, email: "pat@example.com" }, "5.6.7.8"); await settle();
const t2 = new URL(mails.at(-1).html.match(/href="([^"]+approve[^"]*)"/)[1].replace(/&amp;/g, "&")).searchParams.get("t");
r = await worker.fetch(req("/api/review", { method: "POST", body: new URLSearchParams({ t: t2 }) }), env, ctx);
check("existing team member skips the invite and is linked to the group", /already on your team/.test(await r.text()) && calls.some((x) => x.url.endsWith("/v1/betaGroups/GRP/relationships/betaTesters")));

// --- decline ---
await post("/api/signup", { ...sam, email: "lee@example.com" }, "9.9.9.9"); await settle();
const t3 = new URL(mails.at(-1).html.match(/href="([^"]+decline[^"]*)"/)[1].replace(/&amp;/g, "&")).searchParams.get("t");
await worker.fetch(req("/api/review", { method: "POST", body: new URLSearchParams({ t: t3 }) }), env, ctx);
check("decline marks the record and calls nobody", (await env.DB.get("s:" + (await _test.idFor("lee@example.com")), "json")).status === "declined");

// --- auto mode ---
env.AUTO_APPROVE = "true";
const invBefore = calls.filter((x) => x.url.endsWith("/v1/userInvitations")).length;
await post("/api/signup", { ...sam, email: "auto@example.com" }, "8.8.8.8"); await settle();
check("auto mode invites without asking", calls.filter((x) => x.url.endsWith("/v1/userInvitations")).length === invBefore + 1 && /auto-invited/.test(mails.at(-1).subject));
env.AUTO_APPROVE = "false";

// --- an email that failed (missing secret) is retried on the next signup from the same address ---
const key = env.RESEND_API_KEY; delete env.RESEND_API_KEY;
const nMails = mails.length;
await post("/api/signup", { ...sam, email: "early@example.com" }, "6.6.6.6"); await settle();
const err = await env.DB.get("cfg:mailError", "json");
check("missing secret: no email, error kept in KV", mails.length === nMails && /secret is missing/.test(err?.error || ""));
env.RESEND_API_KEY = key;
await post("/api/signup", { ...sam, email: "early@example.com" }, "6.6.6.6"); await settle();
check("repeat signup retries the owner email once secrets exist", mails.length === nMails + 1 && /early@example.com/.test(mails.at(-1).html));
await post("/api/signup", { ...sam, email: "early@example.com" }, "6.6.6.6"); await settle();
check("…and stays quiet after it was sent", mails.length === nMails + 1);

// --- rate limit ---
for (let i = 0; i < 5; i++) await post("/api/signup", { ...sam, email: `r${i}@example.com` }, "7.7.7.7");
r = await post("/api/signup", { ...sam, email: "r9@example.com" }, "7.7.7.7"); await settle();
check("6th signup from one IP in an hour is refused", r.status === 429);

// --- removal ---
const delCalls = calls.length;
r = await post("/api/remove", { email: "sam@example.com" }); await settle();
check("remove deletes our record and tells the owner, never calls Apple",
  r.status === 200 && !(await env.DB.get("s:" + id)) && /remove sam@example.com/.test(mails.at(-1).subject) && calls.length === delCalls);

// --- owner status page ---
r = await worker.fetch(req("/api/status?k=wrong"), env, ctx);
check("status page hidden without the right key", r.status === 404);
r = await worker.fetch(req("/api/status?k=test-secret&mail=1&asc=1"), env, ctx);
const st = await r.json(), stText = JSON.stringify(st);
check("status page reports secrets, mail test and ASC ids without leaking values",
  st.secrets.RESEND_API_KEY.startsWith("set") && st.mailTest.ok && st.asc.app === "APP1" && st.asc.internalGroup === "GRP" && !stText.includes("re_test") && !stText.includes("PRIVATE KEY") && !stText.includes("test-secret"));

// --- missing LINK_SECRET: no crash, the reason is recorded and reported ---
const ls = env.LINK_SECRET; delete env.LINK_SECRET;
r = await worker.fetch(req("/api/status?k=x"), env, ctx);
check("status page explains a missing LINK_SECRET instead of crashing", r.status === 500 && /LINK_SECRET/.test((await r.json()).error));
r = await post("/api/signup", { ...sam, email: "nolink@example.com" }, "4.4.4.4"); await settle();
check("signup still answers ok and records why no email went out", r.status === 200 && /LINK_SECRET/.test((await env.DB.get("cfg:mailError", "json")).error));
env.LINK_SECRET = ls;

// --- secrets never leak to the browser ---
const bodies = await Promise.all([post("/api/signup", { email: "x" }, "3.3.3.3"), post("/api/remove", {})].map((p) => p.then((x) => x.text())));
check("API responses carry no secrets", !bodies.some((b) => b.includes("test-secret") || b.includes("PRIVATE KEY") || b.includes("re_test")));

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
