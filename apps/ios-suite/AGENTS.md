# AGENTS.md: Cratebox Suite (iOS)

> Monorepo (2026-11-11): this folder is `apps/ios-suite/` in zonahbear/Cratebox. Paths below are relative to it; workflows
> live in the root `.github/workflows/`. Start at the root [AGENTS.md](../../AGENTS.md).

Read this first. Keep it short.

## Rules

- **Device sizes:** [`docs/device-sizes.md`](docs/device-sizes.md) is the only source for screen sizes, scales, safe
  areas and Display Zoom sizes, for the shipping app and for the personal HEAT build (`personal/heat`). Never estimate a
  size. If a device is missing, measure it (ios.yml, `measure: true`) and add it there first.
- HEAT never goes into the shipping app (`com.zonahbear.cratebox.suite`). It lives only on `personal/heat`
  (`com.zonahbear.cratebox.heat`), which never merges back.
- Installs only via TestFlight (sideloading retired). macOS CI is manual-only. ios.yml defaults to the `xcode-27` runner
  (Apple Silicon, iOS 27 SDK, needed for AI mode's Music Understanding); `macos-15-intel` is the fallback (input `runner`).
- AI features stay behind Settings → AI mode (`cb.ai`, off by default) and on-device only. See breadcrumbs 2026-11-11.

## Breadcrumbs

Session notes and next steps: [`.claudes/breadcrumbs.md`](.claudes/breadcrumbs.md).
