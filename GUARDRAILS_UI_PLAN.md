# Guardrails UI implementation plan

The first usable settings UI is implemented in `app/frontend/admin.html` and `app/frontend/js/admin.js`. This plan defines the intended behavior for a future component-based redesign or further UI work.

## 1. Settings layout

Keep three distinct cards in this order:

1. **Business context** — the trusted facts that determine what is relevant and what answer agents may use.
2. **Providers and agents** — global Groq/OpenRouter credentials plus a provider, model, and optional credential override for every operational agent.
3. **Independent guardrails** — enable switch, provider/model, optional key override, failure policy, classifier prompt, and each customer-facing blocked reply.

This order makes the scope dependency visible: business context defines relevance, and guardrails enforce it.

## 2. Secret handling

- Never place a stored key in an API response or HTML value.
- Show only “saved” or “not saved” state using the `*_configured` booleans from `GET /api/settings/config`.
- A blank key input preserves the existing value.
- Require an explicit clear action before sending an empty string to erase saved keys.
- Keep provider-specific global keys separate from optional per-agent overrides.

## 3. Provider and model behavior

- Provider choices are `groq` and `openrouter`.
- Preserve custom model identifiers exactly; OpenRouter identifiers normally use `provider/model` format.
- When the provider changes, retain the current model but warn if its format appears incompatible.
- Explain that agent-specific keys override the selected provider's global key.
- Add a connection test per provider in a later iteration. It should report authentication/model errors without echoing credentials.

## 4. Guardrail editor behavior

- Make the enabled switch, local heuristic switch, and fail policy visually prominent.
- Label `block` as the recommended production policy and explain that `allow` continues when classification fails.
- Keep the system prompt editable in a large monospace field.
- Keep the prompt-injection, irrelevant-query, and failure replies independently editable.
- Validate every model and guardrail text field before saving; focus the first invalid field.
- Warn before disabling guardrails or selecting fail open.

## 5. Test panel

Use `POST /api/settings/guardrails/test` with `{ "message": "..." }`. Display:

- decision: `allow`, `prompt_injection`, `irrelevant`, or `error`;
- short reason;
- source: `heuristic`, `model`, or `failure_policy`.

The test uses saved settings. Keep “Save” and “Test” separate and clearly indicate unsaved changes. Provide three one-click samples: a normal business question, an unrelated question, and an instruction override attempt.

## 6. Error and accessibility requirements

- Use inline errors alongside toasts for failed saves and tests.
- Preserve entered non-secret values after an error.
- Associate every input with a `for`/`id` label, expose result changes through an `aria-live` region, and support keyboard-only use.
- Do not communicate decisions using color alone.
- On narrow screens, stack fields in the same order as desktop.

## 7. Acceptance checks

- Switching any agent to OpenRouter and entering a custom model persists after reload.
- Key values never appear in settings responses, page source, logs, or network response bodies.
- A common injection attempt is blocked before the supervisor runs.
- An unrelated question gets the configured irrelevant reply.
- A relevant follow-up is allowed using recent conversation context.
- Fail closed returns the configured failure reply when the guardrail provider is unavailable.
- Fail open continues to the supervisor under the same failure.
- Disabled guardrails bypass classification explicitly.
- Settings work under the deployed origin without a localhost URL.
