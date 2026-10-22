// =====================================================================================
//  Cratebox site Worker: serves site/dist (landing page, privacy, web player) and runs the iOS beta signup
// =====================================================================================
// Signups become INTERNAL TestFlight testers, which Apple only allows for App Store Connect team members:
//   1. POST /api/signup stores {first, last, email} in KV as "pending" and emails the owner signed
//      Approve / Decline links (or invites at once when AUTO_APPROVE is "true").
//   2. Approve sends an App Store Connect user invitation (role ASC_ROLE, this app only, no provisioning).
//   3. The person accepts Apple's email. The cron (scheduled) sees them in /v1/users and adds them to the
//      internal beta group, which makes TestFlight email them the build.
// Secrets (wrangler secret put): ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8, RESEND_API_KEY, ADMIN_EMAIL, LINK_SECRET.
// None of them ever reach the browser: the pages only see {ok} or {error}.

const ASC = "https://api.appstoreconnect.apple.com";
const LINK_DAYS = 7, SEATS = 100;
const enc = new TextEncoder();

const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
const b64u = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const b64uStr = (s) => b64u(enc.encode(s));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const normEmail = (e) => String(e || "").trim().toLowerCase();
const okEmail = (e) => e.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e);
const clean = (s, n = 60) => String(s || "").replace(/[\u0000-\u001f<>]/g, "").trim().slice(0, n);

// Records live under "s:<id>" with the status mirrored into KV metadata, so the cron can list without reads.
async function idFor(email) {
  return b64u(await crypto.subtle.digest("SHA-256", enc.encode(email))).slice(0, 22);
}
async function getRec(env, id) { return env.DB.get("s:" + id, "json"); }
async function putRec(env, r) {
  r.updated = new Date().toISOString();
  await env.DB.put("s:" + r.id, JSON.stringify(r), { metadata: { status: r.status } });
  return r;
}
async function listRecs(env) {
  const out = []; let cursor;
  do {
    const page = await env.DB.list({ prefix: "s:", cursor });
    out.push(...page.keys); cursor = page.list_complete ? null : page.cursor;
  } while (cursor);
  return out;
}

// ---- signed approve/decline links: HMAC over "id.action.expiry", so a forwarded email can't be edited ----
async function hmacKey(env) {
  if (!env.LINK_SECRET) throw new Error("LINK_SECRET secret is missing");
  return crypto.subtle.importKey("raw", enc.encode(env.LINK_SECRET), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}
async function makeToken(env, id, action, now = Date.now()) {
  const body = `${id}.${action}.${Math.floor(now / 1000) + LINK_DAYS * 86400}`;
  return body + "." + b64u(await crypto.subtle.sign("HMAC", await hmacKey(env), enc.encode(body)));
}
async function readToken(env, t, now = Date.now()) {
  const p = String(t || "").split(".");
  if (p.length !== 4 || !["approve", "decline"].includes(p[1])) return null;
  const body = p.slice(0, 3).join(".");
  const sig = Uint8Array.from(atob(p[3].replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
  if (!(await crypto.subtle.verify("HMAC", await hmacKey(env), sig, enc.encode(body)))) return null;
  if (+p[2] * 1000 < now) return { expired: true };
  return { id: p[0], action: p[1] };
}

// ---- App Store Connect: ES256 JWT from the .p8, then plain JSON:API calls ----
let jwtCache = null;
async function ascToken(env) {
  const now = Math.floor(Date.now() / 1000);
  if (jwtCache && jwtCache.exp - 60 > now) return jwtCache.tok;
  const pem = env.ASC_KEY_P8.replace(/\\n/g, "\n").replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  const der = Uint8Array.from(atob(pem), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey("pkcs8", der, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  const exp = now + 15 * 60;
  const head = b64uStr(JSON.stringify({ alg: "ES256", kid: env.ASC_KEY_ID, typ: "JWT" }));
  const claims = b64uStr(JSON.stringify({ iss: env.ASC_ISSUER_ID, iat: now, exp, aud: "appstoreconnect-v1" }));
  // WebCrypto ECDSA already returns raw r||s, which is exactly what JWS ES256 wants.
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, enc.encode(head + "." + claims));
  jwtCache = { tok: `${head}.${claims}.${b64u(sig)}`, exp };
  return jwtCache.tok;
}
async function asc(env, method, path, body) {
  const r = await fetch(ASC + path, {
    method, body: body ? JSON.stringify(body) : undefined,
    headers: { authorization: "Bearer " + (await ascToken(env)), "content-type": "application/json" },
  });
  const text = await r.text();
  let data = null; try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
  return { ok: r.ok, status: r.status, data, detail: data?.errors?.map((e) => e.detail || e.title).join("; ") || "" };
}

// App and internal group ids are looked up once from the bundle id and cached in KV.
async function appId(env) {
  let id = await env.DB.get("cfg:app");
  if (id) return id;
  const r = await asc(env, "GET", `/v1/apps?filter[bundleId]=${encodeURIComponent(env.ASC_BUNDLE_ID)}&limit=1`);
  id = r.data?.data?.[0]?.id;
  if (!id) throw new Error(`App Store Connect has no app with bundle id ${env.ASC_BUNDLE_ID} (${r.status} ${r.detail})`);
  await env.DB.put("cfg:app", id);
  return id;
}
async function groupId(env) {
  let id = await env.DB.get("cfg:group");
  if (id) return id;
  const r = await asc(env, "GET", `/v1/apps/${await appId(env)}/betaGroups?limit=200`);
  const groups = (r.data?.data || []).filter((g) => g.attributes?.isInternalGroup);
  const want = (env.ASC_GROUP_NAME || "").trim().toLowerCase();
  const g = want ? groups.find((x) => x.attributes.name.toLowerCase() === want) : groups[0];
  if (!g) throw new Error(want ? `No internal TestFlight group named "${env.ASC_GROUP_NAME}"` : "The app has no internal TestFlight group yet: make one in App Store Connect → TestFlight");
  await env.DB.put("cfg:group", g.id);
  return g.id;
}

async function findUser(env, email) {
  const r = await asc(env, "GET", `/v1/users?filter[username]=${encodeURIComponent(email)}&limit=1`);
  return r.data?.data?.[0] || null;
}

// Step 2: team invite, limited to this one app. Someone already on the team skips straight to the group.
async function invite(env, rec) {
  if (await findUser(env, rec.email)) return addToGroup(env, rec);
  const r = await asc(env, "POST", "/v1/userInvitations", {
    data: {
      type: "userInvitations",
      attributes: { email: rec.email, firstName: rec.first, lastName: rec.last, roles: [env.ASC_ROLE || "MARKETING"], allAppsVisible: false, provisioningAllowed: false },
      relationships: { visibleApps: { data: [{ type: "apps", id: await appId(env) }] } },
    },
  });
  // 409 = an invitation for this email is already out; treat it as sent.
  if (!r.ok && r.status !== 409) throw new Error(`Apple refused the team invite (${r.status}): ${r.detail}`);
  rec.status = "invited"; rec.invited = new Date().toISOString();
  return putRec(env, rec);
}

// Step 3: once they're a team user, make them a tester in the internal group.
async function addToGroup(env, rec) {
  const gid = await groupId(env);
  let r = await asc(env, "POST", "/v1/betaTesters", {
    data: { type: "betaTesters", attributes: { email: rec.email, firstName: rec.first, lastName: rec.last }, relationships: { betaGroups: { data: [{ type: "betaGroups", id: gid }] } } },
  });
  if (r.status === 409) {
    // Already a tester (e.g. of another group): link the existing tester to this group instead.
    const f = await asc(env, "GET", `/v1/betaTesters?filter[email]=${encodeURIComponent(rec.email)}&limit=1`);
    const tid = f.data?.data?.[0]?.id;
    r = tid ? await asc(env, "POST", `/v1/betaGroups/${gid}/relationships/betaTesters`, { data: [{ type: "betaTesters", id: tid }] }) : f;
  }
  if (!r.ok) throw new Error(`Apple refused adding them to the TestFlight group (${r.status}): ${r.detail}`);
  rec.status = "added"; rec.added = new Date().toISOString();
  return putRec(env, rec);
}

// ---- email to the owner (Resend). Testers get Apple's own emails, never ours. ----
// Returns whether Resend took it. The last failure is kept in KV as "cfg:mailError" so it can be read from the
// Cloudflare dashboard (Workers KV → cratebox) without digging through logs.
async function mail(env, subject, html) {
  let err;
  if (!env.RESEND_API_KEY || !env.ADMIN_EMAIL) err = "RESEND_API_KEY or ADMIN_EMAIL secret is missing";
  else {
    try {
      const r = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: { authorization: "Bearer " + env.RESEND_API_KEY, "content-type": "application/json" },
        body: JSON.stringify({ from: env.MAIL_FROM || "Cratebox <onboarding@resend.dev>", to: [env.ADMIN_EMAIL], subject, html }),
      });
      if (r.ok) return true;
      err = `Resend ${r.status}: ${(await r.text()).slice(0, 300)}`;
    } catch (e) { err = "Resend unreachable: " + e.message; }
  }
  console.log("mail failed:", err, "|", subject);
  await env.DB.put("cfg:mailError", JSON.stringify({ at: new Date().toISOString(), subject, error: err }));
  return false;
}
async function seatsUsed(env) {
  return (await listRecs(env)).filter((k) => ["invited", "added"].includes(k.metadata?.status)).length;
}
const btn = (href, label, bg) => `<a href="${esc(href)}" style="display:inline-block;padding:10px 18px;margin-right:8px;border-radius:4px;background:${bg};color:#000;font:600 15px system-ui;text-decoration:none">${label}</a>`;

async function askOwner(env, rec, base) {
  try { return await askOwnerInner(env, rec, base); }
  catch (e) {
    console.log("askOwner failed:", e.message);
    await env.DB.put("cfg:mailError", JSON.stringify({ at: new Date().toISOString(), subject: "approval email for " + rec.email, error: e.message }));
  }
}
async function askOwnerInner(env, rec, base) {
  const a = `${base}/api/review?t=${await makeToken(env, rec.id, "approve")}`;
  const d = `${base}/api/review?t=${await makeToken(env, rec.id, "decline")}`;
  rec.notified = await mail(env, `Cratebox beta request: ${rec.first} ${rec.last}`,
    `<p style="font:15px system-ui">${esc(rec.first)} ${esc(rec.last)} (<b>${esc(rec.email)}</b>) asked to join the iOS beta.<br>${await seatsUsed(env)} of ${SEATS} tester seats used.</p>
     <p>${btn(a, "Approve", "#3ddc84")}${btn(d, "Decline", "#cfd4dc")}</p>
     <p style="font:12px system-ui;color:#666">Approve sends an App Store Connect team invite (${esc(env.ASC_ROLE || "MARKETING")} role, Cratebox only). Links expire in ${LINK_DAYS} days and ask you to confirm before anything happens.</p>`);
  return putRec(env, rec);
}

// ---- pages for the approve link: GET shows a confirm button (mail scanners prefetch GETs), POST acts ----
const page = (title, body) => new Response(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title>
<body style="margin:0;background:#0b0d10;color:#e6e9ee;font:16px/1.5 system-ui;padding:40px max(16px,env(safe-area-inset-left))"><div style="max-width:520px;margin:0 auto">
<h1 style="font:700 30px 'Arial Narrow',system-ui;letter-spacing:.04em;text-transform:uppercase">${esc(title)}</h1>${body}</div></body>`,
  { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "x-robots-tag": "noindex" } });

async function review(req, env) {
  const form = req.method === "POST" ? await req.formData() : null;
  const t = form ? form.get("t") : new URL(req.url).searchParams.get("t");
  const tok = await readToken(env, t);
  if (!tok) return page("Link not valid", "<p>This link was changed or isn't a Cratebox approve link.</p>");
  if (tok.expired) return page("Link expired", `<p>Approve links last ${LINK_DAYS} days. The request is still saved: if they sign up again with the same email, you get a fresh email.</p>`);
  const rec = await getRec(env, tok.id);
  if (!rec) return page("Request not found", "<p>This signup was deleted.</p>");
  const who = `${esc(rec.first)} ${esc(rec.last)} &lt;${esc(rec.email)}&gt;`;
  if (rec.status !== "pending" && rec.status !== "failed") return page("Already handled", `<p>${who} is <b>${esc(rec.status)}</b>.</p>`);
  if (!form) {
    const verb = tok.action === "approve" ? "Approve" : "Decline";
    return page(`${verb} request?`, `<p>${who}</p><form method="post"><input type="hidden" name="t" value="${esc(t)}">
      <button style="padding:12px 22px;border:0;border-radius:4px;font:700 17px system-ui;background:${tok.action === "approve" ? "#3ddc84" : "#cfd4dc"};color:#000;cursor:pointer">${verb}</button></form>`);
  }
  if (tok.action === "decline") {
    rec.status = "declined"; await putRec(env, rec);
    return page("Declined", `<p>${who} won't be invited. They aren't told.</p>`);
  }
  try {
    await invite(env, rec);
    return page("Approved", rec.status === "added"
      ? `<p>${who} was already on your team, so they're now in the TestFlight group.</p>`
      : `<p>Apple is emailing ${who} a team invite. Once they accept, they're added to TestFlight automatically (checked every 15 minutes).</p>`);
  } catch (e) {
    rec.status = "failed"; rec.note = e.message; await putRec(env, rec);
    return page("Couldn't invite", `<p>${esc(e.message)}</p><p>The request is saved as failed; this link still works once it's fixed.</p>`);
  }
}

// ---- public API ----
async function signup(req, env, ctx) {
  let b; try { b = await req.json(); } catch { return json({ error: "Send the form again." }, 400); }
  if (b.website) return json({ ok: true }); // honeypot: bots fill every field
  const email = normEmail(b.email), first = clean(b.first), last = clean(b.last);
  if (!first || !last) return json({ error: "Add your first and last name." }, 400);
  if (!okEmail(email)) return json({ error: "That email doesn't look right." }, 400);
  if (!b.consent) return json({ error: "Tick the box to say you understand it's a beta." }, 400);

  // 5 signups per IP per hour is plenty for people and dull for scripts.
  const ip = req.headers.get("cf-connecting-ip") || "?", rk = "rl:" + ip;
  const n = +((await env.DB.get(rk)) || 0);
  if (n >= 5) return json({ error: "Too many requests from here. Try again in an hour." }, 429);
  await env.DB.put(rk, String(n + 1), { expirationTtl: 3600 });

  const id = await idFor(email);
  const old = await getRec(env, id);
  // Same answer for repeats so the form can't be used to check who signed up.
  const base = env.SITE_URL || new URL(req.url).origin;
  if (old && old.status !== "declined") {
    // A pending request whose email never went out (e.g. secrets weren't set yet) or whose links have expired
    // gets a fresh email; anything else is left alone.
    if (old.status === "pending" && (!old.notified || Date.now() - Date.parse(old.updated) > LINK_DAYS * 86400e3)) ctx.waitUntil(askOwner(env, old, base));
    return json({ ok: true });
  }
  const rec = await putRec(env, { id, email, first, last, status: "pending", created: new Date().toISOString() });
  if (env.AUTO_APPROVE === "true") {
    ctx.waitUntil(invite(env, rec).then(
      (r) => mail(env, `Cratebox beta: auto-invited ${rec.first} ${rec.last}`, `<p>${esc(rec.email)} is now <b>${r.status}</b>.</p>`),
      async (e) => { rec.status = "failed"; rec.note = e.message; await putRec(env, rec); await askOwner(env, rec, base); }));
  } else ctx.waitUntil(askOwner(env, rec, base));
  return json({ ok: true });
}

// Deletes only our copy. Removing someone from the Apple team stays a manual step for the owner, so this
// public form can never take a real team member (or the owner) off App Store Connect.
async function remove(req, env, ctx) {
  let b; try { b = await req.json(); } catch { return json({ error: "Send the form again." }, 400); }
  const email = normEmail(b.email);
  if (!okEmail(email)) return json({ error: "That email doesn't look right." }, 400);
  const id = await idFor(email), rec = await getRec(env, id);
  if (rec) {
    await env.DB.delete("s:" + id);
    if (rec.status === "invited" || rec.status === "added")
      ctx.waitUntil(mail(env, `Cratebox beta: remove ${rec.email} from App Store Connect`,
        `<p>${esc(rec.first)} ${esc(rec.last)} (${esc(rec.email)}) asked for their data to be deleted. Their signup is gone; please remove them in App Store Connect → Users and Access (and TestFlight) within a few days.</p>`));
  }
  return json({ ok: true });
}

// ---- owner-only status page: /api/status?k=<LINK_SECRET>[&mail=1][&asc=1] ----
// Says which secrets are set (never their values), the last mail error and signup counts; mail=1 sends a test
// email and shows Resend's answer, asc=1 checks the App Store Connect key, app and internal group.
async function status(req, env) {
  const q = new URL(req.url).searchParams;
  if (!env.LINK_SECRET) return json({ error: "LINK_SECRET secret is missing, so this page can't check your key" }, 500);
  const want = await hmacKey(env);
  const a = await crypto.subtle.sign("HMAC", want, enc.encode(q.get("k") || "")), b = await crypto.subtle.sign("HMAC", want, enc.encode(env.LINK_SECRET));
  if (b64u(a) !== b64u(b)) return json({ error: "Not found" }, 404);
  const names = ["ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_KEY_P8", "RESEND_API_KEY", "ADMIN_EMAIL", "LINK_SECRET"];
  const out = {
    secrets: Object.fromEntries(names.map((n) => [n, env[n] ? `set (${String(env[n]).length} chars)` : "MISSING"])),
    adminEmail: env.ADMIN_EMAIL ? env.ADMIN_EMAIL.replace(/^(.).*(@.*)$/, "$1…$2") : null,
    mailFrom: env.MAIL_FROM, siteUrl: env.SITE_URL,
    lastMailError: await env.DB.get("cfg:mailError", "json"),
    signups: {},
  };
  for (const k of await listRecs(env)) out.signups[k.metadata?.status || "?"] = (out.signups[k.metadata?.status || "?"] || 0) + 1;
  if (q.get("mail")) {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { authorization: "Bearer " + env.RESEND_API_KEY, "content-type": "application/json" },
      body: JSON.stringify({ from: env.MAIL_FROM || "Cratebox <onboarding@resend.dev>", to: [env.ADMIN_EMAIL], subject: "Cratebox test email", html: "<p>The site can email you.</p>" }),
    }).catch((e) => ({ ok: false, status: 0, text: async () => e.message }));
    out.mailTest = { ok: r.ok, status: r.status, resend: (await r.text()).slice(0, 400) };
  }
  if (q.get("asc")) {
    try { await env.DB.delete("cfg:app"); await env.DB.delete("cfg:group"); out.asc = { app: await appId(env), internalGroup: await groupId(env) }; }
    catch (e) { out.asc = { error: e.message }; }
  }
  return json(out);
}

// ---- cron: finish invites for people who accepted Apple's email ----
async function sweep(env) {
  for (const k of await listRecs(env)) {
    if (k.metadata?.status !== "invited") continue;
    const rec = await getRec(env, k.name.slice(2));
    if (!rec) continue;
    try {
      if (!(await findUser(env, rec.email))) continue; // hasn't accepted yet
      await addToGroup(env, rec);
      await mail(env, `Cratebox beta: ${rec.first} ${rec.last} is in TestFlight`, `<p>${esc(rec.email)} accepted the team invite and was added to the TestFlight group.</p>`);
    } catch (e) {
      rec.status = "failed"; rec.note = e.message; await putRec(env, rec);
      const retry = `${env.SITE_URL}/api/review?t=${await makeToken(env, rec.id, "approve")}`;
      await mail(env, `Cratebox beta: couldn't add ${rec.email} to TestFlight`,
        `<p>${esc(e.message)}</p><p>${btn(retry, "Try again", "#3ddc84")} or add them by hand in App Store Connect → TestFlight.</p>`);
    }
  }
}

export default {
  async fetch(req, env, ctx) {
    try { return await route(req, env, ctx); }
    catch (e) {
      // Error messages here never contain secret values; they name what's missing or what Apple/Resend said.
      console.log("unhandled:", e.stack || e.message);
      return json({ error: "Server error: " + e.message }, 500);
    }
  },
  async scheduled(_ev, env, ctx) { ctx.waitUntil(sweep(env)); },
};

async function route(req, env, ctx) {
    const { pathname } = new URL(req.url);
    if (pathname === "/api/signup" && req.method === "POST") return signup(req, env, ctx);
    if (pathname === "/api/remove" && req.method === "POST") return remove(req, env, ctx);
    if (pathname === "/api/review" && (req.method === "GET" || req.method === "POST")) return review(req, env);
    if (pathname === "/api/status" && req.method === "GET") return status(req, env);
    if (pathname.startsWith("/api/")) return json({ error: "Not found" }, 404);
    // Assets run with html_handling "none" (no redirects for the player's PWA), so folders need their index here.
    if (pathname.endsWith("/")) return env.ASSETS.fetch(new Request(new URL(pathname + "index.html", req.url), req));
    return env.ASSETS.fetch(req);
}

export const _test = { makeToken, readToken, ascToken, idFor, sweep, resetJwt: () => { jwtCache = null; } };
