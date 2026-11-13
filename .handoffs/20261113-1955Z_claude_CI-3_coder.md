Task CI-3 (self-hosted M4 runner) · branch ci/self-hosted-runner · base main df8daab · head = the commit carrying this memo · PR https://github.com/zonahbear/Cratebox/pull/30 (+ suite https://github.com/zonahbear/cratebox-iOS-suite/pull/32 into claude/ios-ai-dj-album-art-settings) · tree clean after push

## 📍 Where We Stopped
- **Active Task:** CI-3. Workflows are done in both repos, as draft PRs. Waiting on Jonah to set up the Mac
  (apps/ios-suite/docs/self-hosted-runner.md) and merge.
- **Current State:** ios.yml and testflight.yml default to runner `m4` = `[self-hosted, macOS, ARM64, cratebox-m4]`.
  `xcode-27` (hosted) is the backup and Intel is removed. Xcode is chosen through DEVELOPER_DIR (no sudo), with an Xcode 27 + arm64 guard.
  TestFlight cleanup removes the profile and the keychain search-list entry. PR #24 merged into main (d249ca3) before this; TestFlight still
  uploads from the suite repo (MONO-4).
- **Blockers/Bugs:** the runner isn't registered yet. Untested: whether simulators boot while the `ci` user is fast-user-switched into the
  background. Security: the suite repo should go private (Jonah's call), and both repos should require approval for fork-PR workflows.

## 🛠️ Environmental Verification
- PASSED (verified, ci/self-hosted-runner in both repos): `actionlint` 1.7.7 with config labels [cratebox-m4, xcode-27],
  `-shellcheck=`, on .github/workflows/ios.yml + testflight.yml.
- PASSED (verified): `python3 -m json.tool .agent/GLOBAL_PLAN.json`.
- No CI run: no runner exists yet. A skipped run is not a pass.

## 📦 Changes Introduced in This Session
- .github/workflows/ios.yml, testflight.yml: runner m4 default, no Intel, no sudo, Xcode 27/arm64 guard, self-hosted cleanup.
- apps/ios-suite/docs/self-hosted-runner.md (new): Mac setup (GitHub security settings, `ci` user, two runners, labels, disk).
- apps/ios-suite/AGENTS.md, .agent/SYSTEM_PROMPT.md, .agent/CONTEXT_MAP.md, TODO.md: runner m4 / xcode-27 wording.
- .agent/GLOBAL_PLAN.json: CI-3 in_progress.
- Suite repo (same branch name): the same workflow edits, docs/self-hosted-runner.md, CLAUDE.md, .claudes/breadcrumbs.md.

## ⏭️ Precise Next Steps for Incoming Model
1. [ ] Jonah: follow docs/self-hosted-runner.md: suite repo private, fork-PR approval on both repos, `ci` user, runners
       m4-suite and m4-mono with label cratebox-m4.
2. [ ] Jonah: merge suite PR #32 into claude/ios-ai-dj-album-art-settings, and Cratebox PR #30 into main.
3. [ ] Agent: run ios.yml once on `m4` (monorepo, main). Check that the log says `RUNNER m4-mono (self-hosted)` + Xcode 27, the tests run, and the screenshots land on
       ci-logs. If the simulators fail under `ci`, move the runner to Jonah's account and update the doc.
4. [ ] Agent: the next phase's TestFlight goes out on `m4` from the suite repo. Set CI-3 done after the first good upload.
5. [ ] Optional (ask Jonah): CI-1 real tracks could be read straight from the Mac's 1 TB drive instead of a private repo + token.
