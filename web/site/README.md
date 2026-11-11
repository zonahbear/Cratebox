# Cratebox website

The public site: landing page, privacy page, the web player at `/player/cratebox.html`, and the iOS beta signup.
It runs as one Cloudflare Worker (free plan). Cloudflare builds it from this private repo itself, so it uses
no GitHub Actions minutes.

```
wrangler.toml          (monorepo root, one level above web/) Worker config: build command, static assets, KV, cron, non-secret settings
site/build.sh          builds site/dist = site/public + a copy of the web player (cratebox.html etc.) in /player
site/public/           index.html (landing), privacy.html
site/src/worker.js     /api/signup, /api/review (approve links), /api/remove, cron that finishes invites
site/test/             node site/test/worker.test.mjs: whole flow against fake Apple / email / KV
```

## How a signup works

1. Someone fills in the form. The Worker saves `{first, last, email}` as **pending** and emails you
   **Approve / Decline** links. The links are signed and last 7 days. Opening one shows a confirm button, so a mail
   scanner that opens links can't approve anyone.
2. **Approve** sends an App Store Connect **team invite** with the `ASC_ROLE` role (default MARKETING). It only
   sees the Cratebox app and gets no certificates or provisioning.
3. They accept Apple's email. Every 15 minutes the cron spots them on the team and adds them to your
   **internal** TestFlight group. TestFlight then emails them the build. You get an email at each step.

Set `AUTO_APPROVE = "true"` in wrangler.toml to skip step 1's approval.

The privacy page's delete form removes the signup from KV. It **never** removes anyone from App Store Connect,
since a public form shouldn't be able to remove your teammates. Instead you get an email asking you to remove them
by hand.

## One-time setup (about 15 minutes)

1. **App Store Connect API key with the Admin role.** Inviting team members needs Admin. The key used for
   TestFlight uploads may be App Manager. In that case make a new one under Users and Access → Integrations →
   App Store Connect API → Team Keys. Note the Key ID, the Issuer ID and the downloaded `.p8` file.
2. **Internal TestFlight group.** In App Store Connect → Cratebox → TestFlight, make sure an internal group exists.
   If you have more than one, put its exact name in `ASC_GROUP_NAME`. Turn on automatic distribution so new
   builds reach testers.
3. **Resend** (free) at resend.com: sign up with the email you want approvals sent to and create an API key.
   With no domain set up, Resend only sends to your own address, which is all this needs.
4. **Cloudflare** (free) at dash.cloudflare.com:
   - Storage & Databases → KV → create a namespace called `cratebox`. Paste its id into `wrangler.toml`
     (already done: `cratebox`). The id isn't a secret.
   - Workers & Pages → Create → Import a repository → pick `zonahbear/Cratebox`. Leave the root directory as `/`,
     the build command empty and the deploy command `npx wrangler deploy`. Cloudflare reads the rest from wrangler.toml.
   - After the first deploy, open the Worker → Settings → Variables and secrets and add these as **Secret**:
     `ASC_KEY_ID`, `ASC_ISSUER_ID`, `ASC_KEY_P8` (the whole .p8 file), `RESEND_API_KEY`, `ADMIN_EMAIL`, and
     `LINK_SECRET` (any long random string, e.g. from a password manager).
   - Put the Worker's address (`https://cratebox.<you>.workers.dev`, or your own domain) into `SITE_URL`.
5. Sign up on the live site with your own email to test. You should get the approve email within a minute.

Each push to the branch Cloudflare watches redeploys the site. Changes to `cratebox.html` at the repo root
reach `/player` on the next deploy.

## Test

`node site/test/worker.test.mjs` (Node 20+). Nothing to install.

## Limits to know

- Apple caps internal testers at 100. Every tester is a member of your App Store Connect team: they can sign in
  there and see the Cratebox app (with the MARKETING role, its store listing, not your other apps or money).
- The signup email must be the tester's Apple ID, or Apple's invite won't match.
- Workers KV free tier: 1,000 writes a day, plenty for signups.
