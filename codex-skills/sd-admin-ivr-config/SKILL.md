---
name: sd-admin-ivr-config
description: Use when configuring, creating, updating, validating, or troubleshooting IVR/script-configuration workflows in the Shandian Intelligent admin backend at ai.sd6g.com:1904, especially tasks involving 话术配置, 智能Agent/智能节点, /api/web IVR APIs, sceneList/sceneListFrontend, prompt Markdown import, intent usage rules, terminal/hangup intents, or direct Bearer token API calls without logging in.
---

# Shandian Admin IVR Config

Use this skill to operate the Shandian Intelligent admin backend by API, not by logging into the page. The default path is: the user provides a valid `Bearer` token, validate it with `/account/findInfo`, then call `/api/web` endpoints directly.

## Non-Negotiables

- Do not use the login page or captcha flow unless there is no valid token and the user explicitly asks for login troubleshooting.
- Do not print, store in docs, or repeat real tokens/passwords in final answers.
- Use request header `token: Bearer <TOKEN>`, not `Authorization`.
- Verify token first with `GET /account/findInfo`; continue only when `code=0`.
- For write operations, create or use a test/new IVR unless the user explicitly asks to modify an existing production IVR.
- For `updateSceneList`, snapshot existing config first and verify by reading it back.
- On Windows, do not use Windows PowerShell 5 for Chinese JSON write requests or inline Chinese payloads; use a UTF-8 Python script or UTF-8 files. PowerShell 5 may mojibake Chinese names/prompts.
- When configuring, checking, or importing a prompt that contains `intent`, read `references/intent-usage-rules.md` first and enforce it against the prompt plus IVR ports/mappings.

## Quick Workflow

1. Extract token from the user's curl or message.
   - Prefer `-H 'token: Bearer ...'`.
   - If only cookie is present, URL decode `token=Bearer%20...`.
2. Validate:
   - `GET https://ai.sd6g.com:1904/api/web/account/findInfo`
   - Header: `token: Bearer <TOKEN>`
3. Read base resources:
   - `GET /industry/findList`
   - `GET /ivr/findAllTtsVoiceBaseInfo`
   - `GET /ivr/findModelList`
   - `POST /ivr/findPage` with `{"query":{"searchName":""},"page":{"current":1,"size":10}}`
4. Create IVR with `/ivr/insert`, or read the target IVR if updating.
5. For smart Agent nodes, clone a known-good scene graph shape from an existing IVR, then replace only business fields.
6. If the prompt contains `intent`, read `references/intent-usage-rules.md`; verify non-hangup intents use current node IDs, hangup intents are exactly the four allowed terminal labels, and labels match IVR ports.
7. Import prompt Markdown as UTF-8. If the prompt is under 10,000 characters, write it unchanged; only compact when it is 10,000+ characters or a readback-verified write fails with `话术场景信息异常`.
8. Verify with `/ivr/findSceneList/{ivrId}` and, when useful, open `/script-graph?ivrId=<ivrId>`.
9. Delete temporary token files or auth dumps.

## Bundled Scripts

- Use `scripts/create_doushen_real_prompt_ivr.py` for "create a new IVR from a stable template + import a UTF-8 prompt" tasks when its parameters fit. It validates the token, clones the template graph, writes raw prompts under 10,000 characters unchanged, falls back to compacted prompt only after length/failure, and reports `promptStrategy`, `promptWrittenChars`, hashes, readback matches, port labels, and terminal nodes.
- Run bundled scripts with a token argument only for the current task; do not hardcode real tokens into scripts, docs, commits, or examples.

## Key API Rules

- Base URL: `https://ai.sd6g.com:1904/api/web`
- IVR pagination payload must be:

```json
{"query":{"searchName":""},"page":{"current":1,"size":10}}
```

- New IVR minimal payload:

```json
{"voiceType":1,"ttsVoiceId":1,"speechRate":1,"name":"<name>","industryId":42}
```

- Smart Agent node type is `type: 4`.
- Agent model config lives at `llmNodeModelConfig`.
- For Chinese scene names, node names, prompts, and graph JSON on Windows, prefer Python `requests` with `json=...`, `ensure_ascii=False`, and explicit UTF-8 file reads/writes. Avoid PowerShell 5 inline Chinese strings for write calls.
- Keep backend and frontend copies in sync:
  - `sceneList[0].nodeList[0]`
  - `sceneListFrontend[0].nodeList[0]`
  - `sceneListFrontend[0].graph.cells[0].data.customData`

## References

Read `references/workflow.md` when you need the detailed end-to-end procedure, payload templates, prompt-length workaround, validation checklist, or troubleshooting notes.

Read `references/intent-usage-rules.md` before configuring, checking, importing, or debugging any prompt that outputs `{"intent":"..."}` or uses terminal/hangup intent labels.
