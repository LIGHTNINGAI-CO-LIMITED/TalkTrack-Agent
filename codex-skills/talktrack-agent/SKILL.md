---
name: talktrack-agent
version: v0.1.17
github_repo: LIGHTNINGAI-CO-LIMITED/TalkTrack-Agent
github_path: codex-skills/talktrack-agent
github_branch: main
description: Use when configuring, creating, updating, validating, troubleshooting, read-only scoring, or drafting outbound smart-Agent prompts for Shandian Intelligent admin IVR workflows at ai.sd6g.com:1904, especially tasks involving arbitrary source-document to outbound prompt generation, 话术配置, 智能Agent/智能节点, 智能信息采集, 对话字段, collectParam, /api/web IVR APIs, sceneList/sceneListFrontend, prompt Markdown import, llmNodeModelConfig, intent/port mapping, terminal/hangup intents, smart-Agent audit scoring, or direct Bearer token API calls without logging in. For ordinary-node TalkTrack-Master work, use the talktrack-master skill instead.
---

# TalkTrack-Agent

Use this TalkTrack-series skill to operate the Shandian Intelligent smart-Agent layer by API, not by logging into the page. The default path is: the user provides a valid `Bearer` token, validate it with `/account/findInfo`, then call `/api/web` endpoints directly.

## Skill Update Check

For backend write/import/configuration tasks, first run the project-level preflight when the workspace is `D:\闪电智能`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\闪电智能\tools\talktrack_skill_preflight.ps1" -Skill talktrack-agent -Mode Write
```

If preflight fails because the local skill is stale and the local GitHub mirror under `D:\闪电智能\github\TalkTrack-Agent` is trusted/current, run the same preflight with `-InstallFromLocalRepo` and re-check. Do not request backend write authorization until preflight prints `PREFLIGHT_PASS`.

At the start of any task using this skill, run the bundled update check:

```powershell
python "C:\Users\luona\.codex\skills\talktrack-agent\scripts\check_skill_update.py" --check
```

If the result is `update_available`, tell the user the local version and GitHub version, then recommend updating before continuing. Do not update automatically. Only when the user confirms, run:

```powershell
python "C:\Users\luona\.codex\skills\talktrack-agent\scripts\check_skill_update.py" --apply
```

If the check fails because GitHub, TLS/certificate chain, or the network is unavailable, do not treat the local skill as up-to-date. Report the local version and failure reason. For backend write/import/configuration tasks, pause and ask the user to update the skill or explicitly approve continuing with the local version. For read-only emergency investigation, you may continue only after stating that update status is unknown. The update check must not use, print, store, or request business API tokens; it only reads the public GitHub skill repository.

### Stale Version Write Gate

For backend write/import/configuration tasks, a stale or unknown skill version is a pre-authorization blocker. Do not ask the user to authorize backend changes such as "授权调整 <ivrId>" until the update gate is resolved.

- If `local_version` is older than `v0.1.11`, stop and require a Skill update or bootstrap first.
- If the project-level preflight script exists, `PREFLIGHT_PASS` is required before any backend write/import/configuration task.
- If the update check returns `check_failed`, stop before backend writes unless the user explicitly says: `我确认接受使用本地旧版 <version> 继续写后台`.
- A generic business authorization such as `授权调整3737` only authorizes the backend scope. It does not authorize using a stale Skill.
- Do not bundle the two approvals together. First resolve Skill version status; only then ask for backend write authorization.

### Old Local Version Bootstrap

If a user or coworker is still on `v0.1.7` and the update check says it is stuck on the local Python certificate chain, the old checker cannot reliably self-update. Do not continue with backend write/import/configuration work under that old skill. Ask them to run the bootstrap updater first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\talktrack-agent\scripts\bootstrap_update_talktrack_agent.ps1"
```

If the local old version does not have `bootstrap_update_talktrack_agent.ps1`, provide the one-time copy-ready bootstrap prompt from Obsidian:

`D:\ObsidianVault\闪电智能知识库\20-Skills\talktrack-agent\TalkTrack-Agent_v0.1.10_旧版自救升级提示词_20260519.md`

## Boundary

- Use this skill for smart Agent / smart-node work: arbitrary source-document to outbound prompt drafting, IVR creation, prompt import, `llmNodeModelConfig`, smart information collection / dialogue fields / `{collectParam}`, intent rules, graph port mappings, terminal / hangup intents, and read-only smart-Agent audits.
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
- After any backend write that changes `sceneListFrontend`, graph `customData`, smart-node prompt, routing intents, model config, or smart information collection fields, run canvas-save validation before declaring success. From the user's perspective, the IVR must open at `/script-graph?ivrId=<ivrId>` and the page must be able to save/update without frontend route/config corruption. If a real browser save click is unavailable, simulate the page-save shape as far as possible, verify the fields the page will read are present, and state the limitation in the report. API readback alone is not enough for graph-affecting writes.
- For smart Agent model parameters, the default and required model is `闪电26BMoE-fast` with `llmNodeModelConfig.id=55`. Do not inherit a template's old model, including `a-qwen3.5-122b-a10b` (`id=41`). When creating, importing, or updating a smart Agent, force `id=55` in backend node, frontend node, and graph `customData`, then read back all three copies.
- Keep raw JSON, full backend snapshots, and large exported artifacts under `D:\闪电智能\tmp`; write durable reports and SOP summaries to the formal Obsidian vault when the user asks for an artifact.
- On Windows, do not use Windows PowerShell 5 for Chinese JSON write requests or inline Chinese payloads; use a UTF-8 Python script or UTF-8 files. PowerShell 5 may mojibake Chinese names/prompts.
- When configuring, checking, or importing a prompt that contains `intent`, read `references/intent-usage-rules.md` first and enforce it against the prompt plus IVR ports/mappings.
- Enforce terminal-closing ownership. If a smart Agent terminal `intent` maps to a later hangup / end node, the Agent must only say a short acknowledgement plus `{"intent":"..."}`; the formal closing sentence, goodbye, handoff promise, and repeated business details belong to the downstream terminal node. Only let the Agent speak the full closing when there is no downstream terminal node that will speak it.
- For smart information collection, prefer the standard configuration: enable the front-page `智能信息采集` switch by setting `llmNodeCollectParamEnabled=1`, define dialogue fields in `llmNodeCollectParamList` with precise descriptions, and insert `{collectParam}` once in the prompt. Use custom inline `param` JSON only when the user explicitly needs full prompt-level control or when the backend workflow requires it. Do not confuse this with the lower `信息采集` switch (`infoCollectEnabled` / `infoCollectConfigList`), which is a separate page section.
- Smart information collection has a dialogue-variable-library gate. Before writing `llmNodeCollectParamList`, confirm every collection field exists in `变量管理 -> 对话字段`; if a field is missing, create it through the variable-management page/API, re-read the variable list, and use the returned real positive field ID in backend node, frontend node, and graph `customData`. Never invent IDs, never use negative temporary IDs such as `-990101`, and never rely on a canvas-only `name` / `desc` pair. A field that saves in the graph but is absent from `变量管理 -> 对话字段` is P0 invalid because `通话详情 -> 对话字段` will not receive usable data.
- If the variable-list or variable-create API is not already known, inspect the page Network calls or frontend interface definitions before writing. If the endpoint and returned field IDs still cannot be confirmed, stop and ask for the endpoint or permission to use the page flow instead of calling `/ivr/updateSceneList` with guessed dialogue fields.
- Dialogue fields are scenario-derived, not fixed defaults. Do not blindly create `客户姓名` / `客户手机号` / `公司名称` for every smart Agent. Infer fields from the user's prompt, source document, business goal, and follow-up workflow; only include PII fields when they are clearly required and authorized.
- For phone-number collection, enforce the confirmation gate: once the Agent has an 11-digit candidate number, it must read the number back to the user and wait for explicit confirmation before treating it as collected, outputting a terminal `intent`, or promising follow-up. If the user denies or corrects the number, update or restart collection and read it back again.
- For contact collection, do not assume every contact method is a phone number. If the user says their WeChat is not a phone number, or offers a non-phone WeChat ID, collect it in a separate `客户微信号` / contact field, keep `客户手机号` empty or unchanged, and use a WeChat-ID readback confirmation gate. Recommended fields are `联系方式类型`, `客户手机号`, `客户微信号`, and `联系方式确认状态` when the scenario needs contact follow-up.
- When creating, importing, or optimizing a smart Agent from a prompt, source document, or business scenario, treat smart information collection as a proactive configuration surface: infer useful dialogue fields, write a `Smart Information Collection Plan`, and, when backend modification is explicitly authorized, enable 智能信息采集 plus the approved fields instead of waiting for a separate request. For read-only validation tasks, report missing fields and do not auto-fix them.

## Quick Workflow

0. Run the Skill Update Check. If a newer GitHub version exists, recommend updating and wait for the user's confirmation before applying it. If the check fails or local version is older than `v0.1.11`, do not ask for backend write authorization yet; first resolve the update/bootstrap gate or obtain an explicit stale-version override using the exact wording in `Stale Version Write Gate`.
1. Classify the task mode before touching APIs: document-to-prompt drafting, smart Agent creation, prompt import, smart information collection design/check, read-only audit, intent / port check, terminal / hangup check, `llmNodeModelConfig` check, or prompt readback validation.
2. Extract token from the user's curl or message.
   - Prefer `-H 'token: Bearer ...'`.
   - If only cookie is present, URL decode `token=Bearer%20...`.
3. Validate:
   - `GET https://ai.sd6g.com:1904/api/web/account/findInfo`
   - Header: `token: Bearer <TOKEN>`
4. Read base resources:
   - `GET /industry/findList`
   - `GET /ivr/findAllTtsVoiceBaseInfo`
   - `GET /ivr/findModelList`; confirm `id=55` is `闪电26BMoE-fast`
   - `POST /ivr/findPage` with `{"query":{"searchName":""},"page":{"current":1,"size":10}}`
5. Create IVR with `/ivr/insert`, or read the target IVR if updating.
6. For smart Agent nodes, clone a known-good scene graph shape from an existing IVR, then replace only business fields.
7. If the prompt contains `intent`, read `references/intent-usage-rules.md`; verify non-hangup intents use current node IDs, hangup intents are exactly the four allowed terminal labels, and labels match IVR ports.
8. If the task involves lead qualification, customer identity, appointment, company, budget, service choice, or other structured follow-up data, read `references/smart-information-collection-v0.1.md`, infer collection fields from the scene, and add `{collectParam}` exactly once to the prompt package. The field list must be generated from the current scene, not copied from a fixed template. If backend writes are authorized, first create/select the approved fields in `变量管理 -> 对话字段`, re-read the variable list, then enable the front-page 智能信息采集 switch (`llmNodeCollectParamEnabled=1`) and configure `llmNodeCollectParamList` with the real positive IDs returned by the variable list.
9. Import prompt Markdown as UTF-8. If the prompt is under 10,000 characters, write it unchanged; only compact when it is 10,000+ characters or a readback-verified write fails with `话术场景信息异常`.
10. Verify with `/ivr/findSceneList/{ivrId}` and run canvas-save validation: open `/script-graph?ivrId=<ivrId>` and confirm the page can save/update, or document why only simulated page-save validation was possible.
11. Delete temporary token files or auth dumps.

## Task Modes

Choose one primary mode and keep the run inside that mode unless the user expands scope:

- `smart-agent-create`: create or assemble an IVR smart Agent from approved source material. Requires explicit write authorization.
- `doc-to-outbound-prompt`: convert arbitrary source documents into an outbound smart-Agent prompt draft. Draft-only; no backend writes.
- `prompt-package-review`: review a generated prompt package for factual grounding, intent rules, privacy risk, length, and import readiness.
- `smart-info-collection-design`: design 智能信息采集 dialogue fields, field descriptions, `{collectParam}` placement, and evidence rules for a smart Agent prompt package. Use this proactively when the scenario implies structured follow-up data, even if the user did not use the exact phrase "智能信息采集".
- `smart-info-collection-configure`: create/select approved scenario-derived fields in `变量管理 -> 对话字段`, re-read the variable list, enable 智能信息采集 (`llmNodeCollectParamEnabled=1`), populate `llmNodeCollectParamList` with the returned real field IDs, update the prompt with `{collectParam}`, and verify backend readback. Requires explicit backend modification authorization and a clear target IVR / smart node. Acceptance requires `llmNodeCollectParamEnabled=1` in backend node, `sceneListFrontend.nodeList`, and graph `customData`; every `llmNodeCollectParamList[].id` must match an existing dialogue field from variable management; `infoCollectEnabled=1` alone is not enough because the visible radio group will still show `不采集`; canvas-save validation must pass or be explicitly reported as simulated-only.
- `smart-info-collection-check`: verify an existing smart Agent prompt/config uses information collection safely, without breaking intent JSON or terminal-closing ownership.
- `prompt-import`: import a Markdown prompt into an existing smart node and validate prompt readback. Requires explicit write authorization.
- `readonly-audit`: inspect existing IVR / smart-node configuration without backend writes.
- `smart-agent-score`: run the smart-Agent read-only audit scorer and produce P0 / P1 / P2 findings plus next-step recommendations.
- `intent-port-check`: verify intent labels, graph ports, terminal nodes, and backend / frontend / graph consistency.
- `terminal-hangup-check`: verify hangup / terminal intent labels follow the four-label rule in `intent-usage-rules.md`.
- `terminal-closing-overlap-check`: verify terminal intent examples in the prompt do not duplicate downstream hangup / end-node closing copy.
- `llm-config-check`: verify `llmNodeModelConfig` exists and is consistent across backend, frontend, and graph custom data.
- `prompt-readback-check`: compare prompt length / hash / required sections against the approved source prompt without printing sensitive prompt material unless the user asks.

## Bundled Scripts

- Use `scripts/check_skill_update.py --check` before starting a task to compare the local skill version with GitHub. The checker prefers `git ls-remote` to read the real remote HEAD SHA, then fetches files by explicit GitHub tree/blob SHA before falling back to Contents API and raw GitHub URLs. It also tries multiple fetch channels: Python `urllib`, `certifi` when installed, `curl.exe`, and PowerShell `WebClient`, so TLS/certificate-chain issues or branch-content cache in one channel do not immediately block the check. Use `--apply` only after the user confirms they want to update the local installed skill.
- Use `scripts/bootstrap_update_talktrack_agent.ps1` when an old local skill cannot self-update because the old Python-only update checker is blocked by local TLS/certificate-chain issues.
- Use `scripts/create_doushen_real_prompt_ivr.py` for "create a new IVR from a stable template + import a UTF-8 prompt" tasks when its parameters fit. It validates the token, clones the template graph, forces the smart-Agent model to `闪电26BMoE-fast` (`llmNodeModelConfig.id=55`) instead of inheriting the template model, writes raw prompts under 10,000 characters unchanged, falls back to compacted prompt only after length/failure, and reports `promptStrategy`, `promptWrittenChars`, hashes, model readback matches, port labels, and terminal nodes.
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
- Smart Agent default model must be `闪电26BMoE-fast` (`llmNodeModelConfig.id=55`). Treat any template-inherited model such as `a-qwen3.5-122b-a10b` (`id=41`) as a configuration bug unless the user explicitly requests an exception.
- Front visible `智能信息采集` state lives at `llmNodeCollectParamEnabled` and field list at `llmNodeCollectParamList`. To make the page show `采集`, set and read back `llmNodeCollectParamEnabled=1` in backend, frontend node list, and graph custom data.
- `llmNodeCollectParamList[].id` must come from `变量管理 -> 对话字段` variable-list readback. Negative IDs, invented IDs, stale template IDs, or name-only fields that do not exist in variable management are invalid even if `/ivr/updateSceneList` accepts the graph JSON.
- Lower `信息采集` model extraction lives at `infoCollectEnabled` and `infoCollectConfigList`. It can coexist with the front switch, but it does not prove the front visible `智能信息采集` radio is enabled.
- When the scenario includes phone-number collection, configure prompt and field descriptions for session-level accumulation of segmented digits; if the lower extractor is used for phone capture, set a recognition round that covers the expected reporting pattern, up to `11` for one-digit-at-a-time reporting.
- Phone-number collection is not complete at "11 digits found"; acceptance requires readback confirmation. Verify prompt rules include: collect fragments, assemble an 11-digit candidate, read it back, wait for user confirmation, handle corrections, and only then continue to follow-up / terminal routing.
- When the scenario includes WeChat collection, distinguish phone-number WeChat from non-phone WeChat ID. Non-phone WeChat IDs may include letters, digits, underscore, hyphen, or mixed spoken tokens; they must be captured separately, read back segment-by-segment, corrected if needed, and confirmed before being treated as collected. Never write a non-phone WeChat ID into `客户手机号`.
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

Read `references/smart-information-collection-v0.1.md` before designing, checking, or importing 智能信息采集 / dialogue-field collection for a smart Agent node.
