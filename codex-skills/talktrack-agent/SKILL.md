---
name: talktrack-agent
description: Use when configuring, creating, updating, validating, troubleshooting, read-only scoring, or drafting outbound smart-Agent prompts for Shandian Intelligent admin IVR workflows at ai.sd6g.com:1904, especially tasks involving arbitrary source-document to outbound prompt generation, 话术配置, 智能Agent/智能节点, /api/web IVR APIs, sceneList/sceneListFrontend, prompt Markdown import, llmNodeModelConfig, intent/port mapping, terminal/hangup intents, smart-Agent audit scoring, or direct Bearer token API calls without logging in. For ordinary-node TalkTrack-Master work, use the talktrack-master skill instead.
---

# TalkTrack-Agent

Use this TalkTrack-series skill to operate the Shandian Intelligent smart-Agent layer by API, not by logging into the page. The default path is: the user provides a valid `Bearer` token, validate it with `/account/findInfo`, then call `/api/web` endpoints directly.

## Boundary

- Use this skill for smart Agent / smart-node work: arbitrary source-document to outbound prompt drafting, IVR creation, prompt import, `llmNodeModelConfig`, intent rules, graph port mappings, terminal / hangup intents, and read-only smart-Agent audits.
- Use `talktrack-master` for TalkTrack-Master ordinary-node work: normal / jump / end nodes, system TTS, knowledge-base answer TTS, NLP / knowledge-base matching, and ordinary-node large-model intent analysis 2.0.
- When one request mixes both layers, split the work by ownership and state which skill owns each layer before reading or writing backend data.

## Non-Negotiables

- Do not use the login page or captcha flow unless there is no valid token and the user explicitly asks for login troubleshooting.
- Do not print, store in docs, or repeat real tokens/passwords in final answers.
- Use request header `token: Bearer <TOKEN>`, not `Authorization`.
- Verify token first with `GET /account/findInfo`; continue only when `code=0`.
- Default to read-only API calls unless the user explicitly authorizes backend modification and the target IVR / node / intent scope is clear.
- Document-to-prompt conversion is draft-only by default. Do not import a generated prompt into the backend until the user explicitly approves the generated prompt package and target IVR / node.
- For write operations, create or use a test/new IVR unless the user explicitly asks to modify an existing production IVR.
- For `updateSceneList`, snapshot existing config first and verify by reading it back.
- Keep raw JSON, full backend snapshots, and large exported artifacts under `D:\闪电智能\tmp`; write durable reports and SOP summaries to the formal Obsidian vault when the user asks for an artifact.
- On Windows, do not use Windows PowerShell 5 for Chinese JSON write requests or inline Chinese payloads; use a UTF-8 Python script or UTF-8 files. PowerShell 5 may mojibake Chinese names/prompts.
- When configuring, checking, or importing a prompt that contains `intent`, read `references/intent-usage-rules.md` first and enforce it against the prompt plus IVR ports/mappings.

## Quick Workflow

0. Classify the task mode before touching APIs: document-to-prompt drafting, smart Agent creation, prompt import, read-only audit, intent / port check, terminal / hangup check, `llmNodeModelConfig` check, or prompt readback validation.
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

## Task Modes

Choose one primary mode and keep the run inside that mode unless the user expands scope:

- `smart-agent-create`: create or assemble an IVR smart Agent from approved source material. Requires explicit write authorization.
- `doc-to-outbound-prompt`: convert arbitrary source documents into an outbound smart-Agent prompt draft. Draft-only; no backend writes.
- `prompt-package-review`: review a generated prompt package for factual grounding, intent rules, privacy risk, length, and import readiness.
- `prompt-import`: import a Markdown prompt into an existing smart node and validate prompt readback. Requires explicit write authorization.
- `readonly-audit`: inspect existing IVR / smart-node configuration without backend writes.
- `smart-agent-score`: run the smart-Agent read-only audit scorer and produce P0 / P1 / P2 findings plus next-step recommendations.
- `intent-port-check`: verify intent labels, graph ports, terminal nodes, and backend / frontend / graph consistency.
- `terminal-hangup-check`: verify hangup / terminal intent labels follow the four-label rule in `intent-usage-rules.md`.
- `llm-config-check`: verify `llmNodeModelConfig` exists and is consistent across backend, frontend, and graph custom data.
- `prompt-readback-check`: compare prompt length / hash / required sections against the approved source prompt without printing sensitive prompt material unless the user asks.

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

Read `references/smart-agent-readonly-audit-v0.1.md` before running a smart-Agent read-only audit scorer or writing its report.

Read `references/document-to-outbound-prompt-v0.1.md` before converting arbitrary source documents into outbound smart-Agent prompt drafts.
