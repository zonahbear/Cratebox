# Cratebox rules (Google Antigravity adapter)

Antigravity loads this file from `.agents/rules/`. It only points at the shared files every agent uses; don't add
rules here, change `.agent/SYSTEM_PROMPT.md` instead. (`.agent/`, singular, is our shared memory folder, not
Antigravity's legacy rules path.)

Read, in order:

1. `.handoffs/LATEST.md`: where the last agent stopped and the next steps.
2. `.agent/SYSTEM_PROMPT.md`: hard rules (they win over anything else you read), starting, handoff, bugs, features, review.
3. `.agent/CONTEXT_MAP.md`: layout, branches, verification commands, workflows.
4. `.agent/GLOBAL_PLAN.json`: the task list. An open PR titled `<TASK-ID>: …` is a claim.
5. The map of the one app you touch: `apps/<app>/AGENTS.md`.

Branch prefix for Antigravity sessions: `antigravity/`.
