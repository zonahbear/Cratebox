# Review checklist (any agent)

Post findings as PR comments, most severe first, each with: file:line, what breaks, a concrete failing scenario,
and a suggested fix. Say what you did **not** check. No style nits unless asked.

## Blockers (request changes)

- Breaks a hard rule in .agent/SYSTEM_PROMPT.md (personal/heat → main, HEAT in the App Store app, audio thread blocking or
  allocating, HEAT safety limits differing, writes to rekordbox sticks, secrets in the diff, unasked merges/releases).
- Wrong behaviour: logic errors, off-by-one in beat/sample maths, units (°F vs °C, seconds vs samples, pt vs px).
- Leftover `<<<<<<<` / `>>>>>>>` markers, debug code, or generated files edited by hand (`apps/linux/src/maps.rs`).
- Workflow changes that trigger on every push or use macOS runners without need.
- Tests removed or skipped to get green.

## Should fix

- A change in one app (web / linux / ios-suite) that the others also implement, with no note in "Other apps".
- Missing CHANGELOG line for a user-facing change; app map not updated after a structure change.
- No handoff memo in `.handoffs/` (and LATEST.md) from the author.

## Verify, don't trust

- Run the app's checks from .agent/CONTEXT_MAP.md ("Deterministic verification") if you can; say which ones ran and which didn't.
- Device sizes only from `apps/ios-suite/docs/device-sizes.md`. BPM/grid claims need real-track evidence.
