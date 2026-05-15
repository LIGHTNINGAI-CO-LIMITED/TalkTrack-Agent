# Smart-Agent Read-Only Audit Scorer v0.1

Use this reference when the user asks for a Shandian admin IVR smart-Agent health check, read-only audit, scorecard, or scoring pilot.

This scorer is for `talktrack-agent` smart Agent / smart-node work. It is not a replacement for `talktrack-master`, which owns ordinary nodes, system TTS, knowledge-base answer TTS, NLP / KB matching, and ordinary-node large-model intent analysis 2.0.

## Hard Boundary

- Read-only only.
- Do not call any endpoint whose path or operation implies `update`, `insert`, `delete`, `save`, or `create`.
- Do not run text debug or voice debug unless the user explicitly changes the scope.
- Do not print, persist, or archive real tokens.
- Do not copy full raw JSON into Obsidian. Keep raw JSON under `D:\闪电智能\tmp` and record only paths in the report.

## Required Inputs

- Target `ivrId`.
- API base, usually `https://ai.sd6g.com:1904/api/web`.
- Token source, preferably Obsidian `secretStorage`, loaded only into the current process environment.
- Optional approved source prompt path. If present, use it for prompt length / hash comparison; if absent, score readback integrity from backend consistency only.

## Recommended Read APIs

Minimum:

```http
GET  /account/findInfo
GET  /ivr/findSceneList/{ivrId}
POST /ivr/findPage
```

Use as needed when the backend exposes the data:

```http
GET  /ivrIntent/findList/{ivrId}
GET  /ivrIntentLevel/findList/{ivrId}
POST /ivrGroup/findPageIvrGroup
GET  /ivr/findAllTtsVoiceBaseInfo
GET  /ivr/findModelList
```

Allowed fallback: additional query-only endpoints may be used when needed for attribution, but write-like endpoint names remain forbidden.

## Raw JSON Layout

Save raw files under:

```text
D:\闪电智能\tmp\sd_admin_readonly_audit_<ivrId>_<YYYYMMDD>
```

Recommended files:

- `account_findInfo.json`
- `ivr_findSceneList_<ivrId>.json`
- `ivr_findPage.json`
- `intent_findList_<ivrId>.json`, if used
- `intent_level_findList_<ivrId>.json`, if used
- `audit_score_summary.json`

## 100-Point Rubric

### 1. Smart Node Structure Integrity: 20

Check:

- IVR exists and `sceneList` / `sceneListFrontend` are readable.
- A smart Agent node exists with `type=4`.
- Intended start node has `isStartNode=true`.
- Backend node, frontend node, and graph `data.customData` refer to the same node identity.
- Graph cells / edges / ports are parseable and do not point to missing nodes.
- Terminal nodes referenced by graph mappings exist.

Typical deductions:

- P0-sized: missing IVR, missing smart node, unparseable graph, missing terminal target.
- P1-sized: backend / frontend / graph mismatch on key node fields.
- P2-sized: naming or display-field inconsistencies that do not affect execution.

### 2. `llmNodeModelConfig` Completeness: 20

Check across backend node, frontend node, and graph custom data:

- `llmNodeModelConfig` exists.
- Model ID is present and matches the expected business choice when specified.
- `prompt` is non-empty.
- Timeout / max speak round fields are present when exposed.
- `enableThinking` / `enable_thinking` is explicit when exposed.
- The three readback surfaces are consistent.

Typical deductions:

- P0-sized: missing model config or empty prompt on the active smart node.
- P1-sized: model ID, timeout, thinking flag, or prompt differs across surfaces.
- P2-sized: optional model metadata missing but behavior appears safe.

### 3. Prompt Readback Integrity: 20

When a source prompt is provided:

- Compare character count and SHA-256 hash after UTF-8 read.
- Confirm backend node, frontend node, and graph custom data contain the same prompt variant.
- Confirm required output format sections remain present, especially intent JSON rules.
- Confirm the prompt was not unexpectedly compacted, truncated, or mojibaked.

When no source prompt is provided:

- Score consistency across backend / frontend / graph.
- Record that source-prompt hash validation was not possible.

Typical deductions:

- P0-sized: prompt missing or unusable.
- P1-sized: prompt readback does not match approved source or differs across surfaces.
- P2-sized: source prompt unavailable, but backend readback is internally consistent.

### 4. Intent / Port Governance: 20

If the prompt or node uses `{"intent":"..."}`, load `intent-usage-rules.md` and check:

- Non-hangup intents use current node IDs or approved business node labels, not stale terminal labels.
- Hangup / terminal intents use exactly the four allowed terminal labels from `intent-usage-rules.md`.
- Smart node `llmNodeIntentList`, `llmNodeIntentMappingList`, frontend `intentList`, graph ports, and terminal nodes agree.
- Terminal mappings point to `type=2`, `nextType=2`, hangup-style terminal nodes when the business meaning is hangup.
- Terminal intent examples in the prompt follow terminal-closing ownership. If an intent maps to a downstream hangup / end node that will speak again, the prompt example must be a short acknowledgement only.
- Terminal intent examples do not duplicate downstream terminal-node closing text, goodbye copy, handoff promises, or business-detail recaps.
- Unknown, stale, duplicated, or unmapped intent labels are listed.

Typical deductions:

- P0-sized: terminal / hangup semantics are broken or map to missing targets.
- P1-sized: prompt intent labels and graph ports disagree, or smart-Agent terminal examples duplicate downstream terminal-node closing copy.
- P2-sized: label naming is confusing but mapped correctly.

### 4.5 Smart Information Collection Governance

If the smart Agent uses 智能信息采集, also check:

- Standard mode uses `{collectParam}` exactly once.
- Dialogue fields have concise field descriptions.
- Field descriptions require evidence from user wording or conversation context.
- Custom inline `param` JSON, if used, has field names matching configured dialogue fields.
- Information collection does not break the required intent JSON format.
- Terminal-closing ownership still holds when terminal replies include collected params.
- PII / sensitive fields are minimized and explicitly justified.

Typical deductions:

- P0-sized: prompt output format is broken and may prevent routing or collection.
- P1-sized: `{collectParam}` missing/duplicated, inline field names mismatch configured fields, or collection asks for unsupported/sensitive data without approval.
- P2-sized: field descriptions are vague but likely recoverable with human review.

### 5. Archive And Security Hygiene: 20

Check this audit run itself:

- Token was not printed into reports, summaries, raw JSON, shell scripts, or temp exports.
- Raw JSON remains under `D:\闪电智能\tmp`.
- Durable report, if requested, is written to `D:\ObsidianVault\闪电智能知识库`.
- Related index pages are updated when a durable report is created.
- `obsidian 'vault=闪电智能知识库' unresolved total` returns `0` when Obsidian was updated.

Typical deductions:

- P0-sized: token leak.
- P1-sized: raw JSON copied into Obsidian or report missing despite request.
- P2-sized: index/report metadata incomplete.

## Issue Severity

- P0: main flow may be unusable, smart node or prompt missing, graph / terminal route broken, 2xx readback impossible, forbidden write occurred, or token leaked.
- P1: configuration likely works but is unstable: backend / frontend / graph mismatch, prompt hash mismatch, port / intent mismatch, partial readback failure.
- P2: improvement item: confusing labels, missing optional metadata, source prompt unavailable for hash comparison, scorer heuristic needs refinement.

## Recommendation Flags

Set these booleans in the final summary:

- `recommendPromptImport`: true when the prompt is missing, stale, truncated, mojibaked, or not readback-consistent.
- `recommendIntentRuleFix`: true when intent labels, terminal labels, ports, mappings, or terminal-closing ownership violate `intent-usage-rules.md`.
- `recommendBackendFix`: true when graph shape, node structure, or model config is broken and cannot be resolved by prompt-only work.
- `recommendLiveDebug`: true only when readback looks structurally sound but live behavior still needs validation.

## `audit_score_summary.json`

Suggested schema:

```json
{
  "ivrId": 0,
  "generatedAt": "YYYY-MM-DDTHH:mm:ss+08:00",
  "totalScore": 0,
  "dimensionScores": {
    "smartNodeStructure": 0,
    "llmNodeModelConfig": 0,
    "promptReadbackIntegrity": 0,
    "intentPortGovernance": 0,
    "archiveAndSecurity": 0
  },
  "p0Items": [],
  "p1Items": [],
  "p2Items": [],
  "recommendPromptImport": false,
  "recommendIntentRuleFix": false,
  "recommendBackendFix": false,
  "recommendLiveDebug": false,
  "smartInformationCollectionCheck": {
    "checked": false,
    "mode": "none",
    "fieldCount": 0,
    "items": []
  },
  "terminalClosingOverlapCheck": {
    "checked": false,
    "overlapCount": 0,
    "items": []
  },
  "rawJsonPaths": [],
  "tokenLeakCheck": "PASS"
}
```

## Report Shape

When the user requests a durable report, include:

1. Boundary: read-only, no backend modification.
2. Inputs and API list.
3. Raw JSON directory path, not raw JSON content.
4. Total score and dimension scores.
5. Smart node structure summary.
6. `llmNodeModelConfig` summary.
7. Prompt readback integrity summary.
8. Intent / port governance summary.
9. Smart information collection summary, if present.
10. Terminal-closing overlap summary, including whether the smart Agent or downstream terminal node owns the final spoken closing.
11. P0 / P1 / P2 issue list.
12. Next-step recommendation flags.
13. Scorer limitations and follow-up improvements.
14. Token leak check result if a token was used.
