# Shandian Admin IVR Workflow Reference

## Auth

Default: do not login.

Use:

```http
token: Bearer <TOKEN>
```

Validate before doing anything:

```http
GET https://ai.sd6g.com:1904/api/web/account/findInfo
```

Expected success:

```json
{"code":"0","message":"success","data":{...}}
```

If `code=7`, the token is invalid or expired. Ask for a fresh token. Do not jump to captcha login unless the user asks.

## Common Request Pattern

On Windows, avoid Windows PowerShell 5 for write requests that contain Chinese scene names, node names, prompts, or graph JSON. Use Python `requests` with UTF-8 file reads/writes for those calls. PowerShell 5 can display or send mojibake even when `ContentType` says UTF-8.

PowerShell is acceptable for ASCII-only reads and quick checks:

```powershell
$base = 'https://ai.sd6g.com:1904/api/web'
$headers = @{ token = 'Bearer <TOKEN>'; 'X-Requested-With' = 'XMLHttpRequest' }
$info = Invoke-RestMethod -Method Get -Uri "$base/account/findInfo" -Headers $headers
```

For JSON POST:

```powershell
$body = @{ query = @{ searchName = '' }; page = @{ current = 1; size = 10 } } |
  ConvertTo-Json -Depth 10 -Compress
$r = Invoke-RestMethod -Method Post -Uri "$base/ivr/findPage" `
  -Headers $headers -ContentType 'application/json;charset=UTF-8' -Body $body
```

For Chinese write payloads, prefer this pattern:

```python
import json, requests

base = "https://ai.sd6g.com:1904/api/web"
headers = {"token": "Bearer <TOKEN>", "X-Requested-With": "XMLHttpRequest"}

payload = {
    "ivrId": 3449,
    "sceneList": json.dumps(scene_list, ensure_ascii=False, separators=(",", ":")),
    "sceneListFrontend": json.dumps(scene_front, ensure_ascii=False, separators=(",", ":")),
}
r = requests.post(f"{base}/ivr/updateSceneList", headers=headers, json=payload, timeout=60)
r.encoding = "utf-8"
data = r.json()
```

## Bundled Creation Script

For "create a new IVR from a stable template + import prompt Markdown" tasks, prefer the skill script when it fits instead of rewriting request code:

```powershell
python scripts/create_doushen_real_prompt_ivr.py --token <TOKEN> --prompt-path <UTF8_MD> --template-ivr-id 3449
```

The script uses Python `requests` and UTF-8 file reads/writes to avoid Windows PowerShell 5 Chinese encoding problems. It applies the raw-prompt policy automatically: prompts under 10,000 characters are written unchanged; compacted prompt is used only when the raw prompt is 10,000+ characters or a raw write fails and a compact fallback is required.

Read its JSON output before reporting success. Key fields are `promptStrategy`, `promptWrittenChars`, `promptCompactedChars`, `promptSha256`, `backendPromptMatches`, `frontendPromptMatches`, `graphPromptMatches`, `portLabels`, and `terminalNodes`.

## Task Mode Routing

Start every run by naming the primary task mode. This prevents smart-Agent creation work, prompt import work, and read-only audit work from accidentally sharing write assumptions.

| Mode | Use For | Write APIs Allowed |
| --- | --- | --- |
| `doc-to-outbound-prompt` | Convert arbitrary source documents into outbound smart-Agent prompt drafts | No |
| `prompt-package-review` | Review a generated prompt package for grounding, privacy, intent rules, length, and import readiness | No |
| `smart-agent-create` | New smart Agent IVR creation from approved source material or a known-good template | Yes, only after explicit user authorization |
| `prompt-import` | Importing or replacing a smart-node Markdown prompt | Yes, only after explicit user authorization |
| `smart-info-collection-design` | Designing 智能信息采集 fields, field descriptions, and `{collectParam}` placement | No by default |
| `smart-info-collection-check` | Checking existing smart information collection prompt/config safety | Read-only by default |
| `readonly-audit` | Readback-only inspection of an existing IVR or smart node | No |
| `smart-agent-score` | Producing a 100-point smart-Agent health score with P0/P1/P2 findings | No |
| `intent-port-check` | Checking prompt intent labels, graph ports, mappings, and terminal nodes | Read-only by default |
| `terminal-hangup-check` | Checking the four allowed hangup / terminal labels and terminal-node behavior | Read-only by default |
| `terminal-closing-overlap-check` | Checking whether smart-Agent terminal examples duplicate downstream hangup / end-node closing copy | Read-only by default |
| `llm-config-check` | Checking `llmNodeModelConfig` across backend, frontend, and graph custom data | Read-only by default |
| `prompt-readback-check` | Checking prompt length, hash, required sections, and readback consistency | Read-only by default |

If the user asks to move from read-only mode to a write mode, pause and restate the exact IVR ID, node scope, intended fields, backup path, and write endpoint before calling any write API.

For source-document conversion, use `references/document-to-outbound-prompt-v0.1.md`. The output is a prompt package, not a backend write. Treat any later import as a separate `prompt-import` task.

For smart information collection, read `references/smart-information-collection-v0.1.md`. Prefer the standard mode: create/select dialogue fields in `变量管理 -> 对话字段`, read the variable list, enable 智能信息采集, configure `llmNodeCollectParamList` with the real returned field IDs, and insert `{collectParam}` once in the prompt. Do not switch to inline `param` JSON unless the user explicitly needs full prompt control or the backend workflow requires it.

Do not directly invent collection fields in canvas JSON. If `llmNodeCollectParamList` uses negative IDs, guessed IDs, stale template IDs, or fields absent from `变量管理 -> 对话字段`, the graph may save but call details will not return usable `对话字段` data.

## Base Reads

Call these before writing:

```http
GET  /industry/findList
GET  /ivr/findAllTtsVoiceBaseInfo
GET  /ivr/findModelList
POST /ivr/findPage
POST /ivrGroup/findPageIvrGroup
```

`/ivr/findPage` uses:

```json
{"query":{"searchName":""},"page":{"current":1,"size":10}}
```

Do not use plain `{"current":1,"size":10}`; it returns `illegal argument`.

## Create IVR

Endpoint:

```http
POST /ivr/insert
```

Minimal payload:

```json
{
  "voiceType": 1,
  "ttsVoiceId": 1,
  "speechRate": 1,
  "name": "<话术名称>",
  "industryId": 42
}
```

Notes:

- `industryId=42` is `教育/K12-其他`; change if the task requires another industry.
- `ttsVoiceId=1` is safe as a default when no voice is specified.
- The response may directly return the new `ivrId`.
- Confirm with `/ivr/findPage` by name.

## Scene Graph Strategy

New IVRs may have `sceneList=null` and `sceneListFrontend=null`.

Do not hand-roll the entire graph if a template exists. Safer pattern:

1. Find an existing IVR with a known-good one-scene smart Agent graph.
2. `GET /ivr/findSceneList/{templateIvrId}`.
3. Copy `data.sceneList` and `data.sceneListFrontend`.
4. Write those strings unchanged to the new IVR with `/ivr/updateSceneList`.
5. If unchanged write succeeds, update business fields in small batches.

Endpoint:

```http
POST /ivr/updateSceneList
```

Payload:

```json
{
  "ivrId": 3449,
  "sceneList": "<JSON string>",
  "sceneListFrontend": "<JSON string>"
}
```

## Smart Agent Node Fields

Smart Agent node:

```json
{
  "type": 4,
  "isStartNode": true,
  "name": "<节点名>",
  "text": "<开场白>",
  "allowInterruptEnabled": true,
  "allowInterruptSecond": 2,
  "llmNodeMaxSpeakRound": 60,
  "llmNodeModelTimeoutMilliSecond": 1000,
  "llmNodeModelConfig": {
    "id": 55,
    "prompt": "<prompt>",
    "enableThinking": 0,
    "enable_thinking": 0
  }
}
```

Model rule:

- Default and required smart-Agent model: `闪电26BMoE-fast`.
- Backend model ID: `llmNodeModelConfig.id=55`.
- Do not inherit a template's previous model. In particular, `a-qwen3.5-122b-a10b` is `id=41` and must be replaced with `id=55` unless the user explicitly approves an exception.
- Force `id=55` in backend node, frontend node, and graph `customData`, then read back all three copies.

Keep these synchronized:

- Backend node: `sceneList[0].nodeList[0]`
- Frontend node: `sceneListFrontend[0].nodeList[0]`
- Graph custom data: `sceneListFrontend[0].graph.cells[0].data.customData`
- Graph display fields:
  - `data.label`
  - `data.title`
  - `data.description`

## Intent Usage Rules

When the prompt contains `{"intent":"..."}`, intent tables, terminal intents, or hangup intents, read `intent-usage-rules.md` before writing or validating the prompt.

Enforce these checks against both the prompt and IVR graph:

- `intent` means the current AI reply's matched flow node or hangup node, not the customer's overall profile or whole-call final evaluation.
- Non-hangup nodes must output the current node ID, for example `stage_1_opening` or `objection_reject`.
- Hangup nodes must output only one of: `高意向成交类`, `待跟进留存类`, `无意向终止类`, `异常场景应急类`.
- `兜底` is not an intent. A fallback/default port may exist in the graph, but prompts, examples, candidate labels, and model output must not use `{"intent":"兜底"}` to jump.
- Do not let earlier customer state lock later intent. The final output follows the current SOP branch and current node mapping.
- Output format must be `回复内容{"intent":"当前意图"}` with JSON directly at the end and no extra explanation.
- If the smart Agent itself is the final speaker, hangup replies must include `再见` and finish the closing sentence before the hangup action.
- If the smart Agent's terminal intent maps to a downstream hangup / end node that will speak again, the Agent must only say a short acknowledgement plus `{"intent":"..."}`. The downstream node owns the formal closing, goodbye, handoff promise, and business-detail recap.

For IVR graph validation, compare the prompt's terminal intent labels with:

- Backend smart node `llmNodeIntentList[].name`
- Backend smart node `llmNodeIntentMappingList`
- Frontend smart node `customData.intentList[].label`
- Frontend port labels/names/text
- Terminal node `type=2`, `nextType=2`, and frontend `actionName=挂机`
- Terminal node spoken text, if present, against terminal examples in the prompt. If both contain the same closing promise, goodbye, or detailed handoff copy, repair the prompt so the smart Agent uses only short acknowledgements.

## Prompt Import

Read Markdown prompts with UTF-8.

For any intent-enabled prompt, load `intent-usage-rules.md` before import and preserve those rules exactly. If compaction is needed, do not rewrite the intent semantics, the four hangup labels, the current-node rule, or the required output format.

Do not compact by default. Count the raw prompt characters first:

- If the raw prompt is under 10,000 characters, write the prompt unchanged.
- If the raw prompt is 10,000+ characters, compact whitespace before writing.
- If an under-10,000 raw prompt still fails with `话术场景信息异常`, test whether a short prompt saves; if short prompt saves, compact and retry.

Compaction rules:

- Remove code fences.
- Remove blank lines.
- Trim trailing spaces.
- Preserve all business wording, intent labels, and rules.

Observed practical limit: a 10418-character prompt failed; a 9686-character compact version saved.

## Validation Checklist

After writing:

```http
GET /ivr/findSceneList/{ivrId}
```

Check:

- `code=0`
- `sceneList` and `sceneListFrontend` are non-null.
- Scene name is expected.
- Smart node has `type=4`.
- Node is start node if intended.
- `llmNodeModelConfig.id=55` in backend node, frontend node, and graph `customData`; the expected model is `闪电26BMoE-fast`.
- Prompt length/hash matches the exact prompt variant written: raw if under 10,000 characters, compacted only when required.
- Prompt matches in backend node, frontend node, and graph custom data.
- For intent-enabled prompts, the imported prompt still follows `intent-usage-rules.md`.
- The prompt does not tell the Agent to output `{"intent":"兜底"}` and does not list `兜底` as a candidate business intent.
- The prompt's four hangup labels match IVR smart-node ports and map to `type=2`, `nextType=2`, `actionName=挂机` terminal nodes.
- Non-hangup intent examples in the prompt are node IDs rather than terminal labels.
- Terminal intent examples do not duplicate downstream terminal-node closing text. If downstream nodes speak the closing, smart-Agent terminal examples are short acknowledgements only.
- If 智能信息采集 is enabled, `{collectParam}` appears exactly once in standard mode, or inline `param` JSON uses exact configured field names in custom mode.
- If 智能信息采集 is enabled, every field referenced by `llmNodeCollectParamList` exists in `变量管理 -> 对话字段`, and every `llmNodeCollectParamList[].id` is the real positive ID returned by the variable list.
- No negative temporary IDs, guessed IDs, stale template IDs, or canvas-only field definitions are present in collection config.
- Dialogue-field descriptions are evidence-based and privacy-minimized.

## Canvas-Save Validation

For any backend write that touches `sceneListFrontend`, graph `customData`, prompt, routing intents, model config, or smart information collection fields, finish with a user-perspective canvas-save validation.

Required checks:

- Open `https://ai.sd6g.com:1904/script-graph?ivrId=<ivrId>`.
- Refresh any already-open old tab before saving; stale page memory can overwrite repaired canvas data.
- Confirm the smart Agent drawer opens and the intended prompt, model, intent ports, and information-collection fields are visible.
- Confirm the page can save/update successfully from the canvas view.
- If a real browser save click is unavailable, simulate the page-save shape as far as possible, verify the fields the page reads are present, and state this limitation in the report.

API readback alone is not enough for graph-affecting writes because the page may rebuild routes or collection fields from frontend canvas data.

Canvas URL:

```text
https://ai.sd6g.com:1904/script-graph?ivrId=<ivrId>
```

## Smart-Agent Read-Only Audit Scorer

Use `references/smart-agent-readonly-audit-v0.1.md` when the user asks for a smart-Agent audit, health check, scorer, or scorecard. The scorer is intentionally separate from `TalkTrack-Master` ordinary-node audits.

Core properties:

- Read-only only. Do not call endpoints containing `update`, `insert`, `delete`, `save`, or `create`.
- Store raw JSON under `D:\闪电智能\tmp`; do not copy full raw JSON into Obsidian.
- Score the current IVR against smart-Agent dimensions: node structure, `llmNodeModelConfig`, prompt readback integrity, intent / port governance, and archive / security hygiene.
- Include smart information collection in prompt/config governance when present: enabled state, dialogue fields, field descriptions, `{collectParam}` or inline `param` usage, and privacy risk.
- Report P0 / P1 / P2 findings, plus whether the next step should be prompt import, intent-rule repair, backend fix, or live debug.
- If a token is used, scan generated report files and raw JSON paths for an exact token leak before final delivery.
- Include terminal-closing overlap findings: whether terminal intent examples in the prompt repeat downstream terminal-node copy, and whether the recommended fix is prompt-only or graph/terminal-node repair.

## Troubleshooting

- `code=7`: token invalid/expired. Ask for a fresh token.
- `illegal argument` on `/ivr/findPage`: use nested `query` and `page`.
- `话术场景信息异常`: graph structure invalid, frontend/backend copies diverged, or prompt too long.
- Mojibake/question marks in Chinese fields: do not embed Chinese literals in Windows PowerShell 5 write requests. Use Python `requests` with UTF-8 files and `ensure_ascii=False`, or another UTF-8-safe client. If mojibake already created a bad test IVR, create a clean IVR and delete the bad one after verifying the clean version.
- Page redirects to `/login`: browser cookie is missing/expired, but API may still work if Header token is valid.

## Security

- Never include real token values in docs or final responses.
- Delete temporary auth files after work.
- Avoid saving browser cookie dumps in the workspace.
