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
- Do not let earlier customer state lock later intent. The final output follows the current SOP branch and current node mapping.
- Output format must be `回复内容{"intent":"当前意图"}` with JSON directly at the end and no extra explanation.
- Hangup replies must include `再见` and finish the closing sentence before the hangup action.

For IVR graph validation, compare the prompt's terminal intent labels with:

- Backend smart node `llmNodeIntentList[].name`
- Backend smart node `llmNodeIntentMappingList`
- Frontend smart node `customData.intentList[].label`
- Frontend port labels/names/text
- Terminal node `type=2`, `nextType=2`, and frontend `actionName=挂机`

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
- `llmNodeModelConfig.id` is expected.
- Prompt length/hash matches the exact prompt variant written: raw if under 10,000 characters, compacted only when required.
- Prompt matches in backend node, frontend node, and graph custom data.
- For intent-enabled prompts, the imported prompt still follows `intent-usage-rules.md`.
- The prompt's four hangup labels match IVR smart-node ports and map to `type=2`, `nextType=2`, `actionName=挂机` terminal nodes.
- Non-hangup intent examples in the prompt are node IDs rather than terminal labels.

Optional browser check:

```text
https://ai.sd6g.com:1904/script-graph?ivrId=<ivrId>
```

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
