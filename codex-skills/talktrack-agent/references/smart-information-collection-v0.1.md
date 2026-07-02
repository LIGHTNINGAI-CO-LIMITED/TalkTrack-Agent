# Smart Information Collection v0.1

Use this reference when a Shandian smart Agent task involves 智能信息采集, 对话字段, information collection, dialogue fields, `{collectParam}`, or inline `param` JSON.

Source basis: Feishu document `【智能信息采集】功能说明书` read through `lark-cli docs +fetch --api-version v2` on 2026-05-15.

## What It Does

智能信息采集 is a smart-Agent-node capability.

When enabled, after each round of conversation between the smart Agent and the user, the system calls a model to analyze the conversation content and the model output, extracts configured business fields, and writes the extracted results to:

```text
通话详情 -> 对话字段
```

This is different from intent routing:

- `intent` drives IVR graph routing.
- information collection writes structured business fields for reporting, follow-up, or CRM-like downstream review.

Do not use collected fields as a substitute for valid `intent` / port mappings.

## Proactive Configuration Rule

When creating, importing, or optimizing a smart Agent from a prompt, source document, or business scenario, smart information collection is not only a check item. Treat it as a configuration surface that can be prepared ahead of time.

Default behavior:

1. Infer only the useful dialogue fields required by the current business goal and prompt, such as customer identity, contact method, company, appointment time, budget, selected service, or follow-up preference when those values are truly part of the scenario.
2. Add a `Smart Information Collection Plan` to the prompt package.
3. Prefer standard configuration: enable the front-page `智能信息采集` switch (`llmNodeCollectParamEnabled=1`), configure dialogue fields in `llmNodeCollectParamList`, and insert `{collectParam}` once in the prompt.
4. If the user has explicitly authorized backend changes for the target IVR / smart node, create or select the approved fields, enable collection, update the prompt, and verify readback.
5. If the task is read-only validation, do not auto-fix missing fields; report the gap and provide the exact field plan needed for the next write pass.

PII rule: names, phone numbers, company names, addresses, and account identifiers can be configured only when the business scenario requires them and the user has authorized collecting them. Use synthetic examples in reports and tests.

Field-list rule: there is no fixed default field set. `客户姓名` / `客户手机号` / `公司名称` are common lead-qualification examples, not mandatory fields. A recruitment call, service-handling call, product-demo call, course call, and quality-review call should each get a different field plan derived from the prompt and follow-up use case.

## Supported Configuration Modes

## Dialogue Variable Library Gate

The standard page flow has an important hidden dependency: smart-Agent collection fields must first exist in `变量管理 -> 对话字段`. The page normally reads that variable list and only lets the operator select valid fields. Directly constructing graph JSON can bypass this guard, so the graph may save while `通话详情 -> 对话字段` remains empty.

Correct write order:

1. Add or confirm each required field in `变量管理 -> 对话字段`.
2. Fetch the variable list through the page/API and record the returned field `id`, `name`, and description.
3. Populate the smart Agent node's `llmNodeCollectParamList` from that variable-list readback.
4. Write the same real IDs into backend node, `sceneListFrontend.nodeList`, and graph `customData`.
5. Re-read both variable management and scene graph before declaring success.

Hard rules:

- `llmNodeCollectParamList[].id` must be a real positive dialogue-field ID returned by variable management.
- Do not use negative temporary IDs such as `-990101`, invented IDs, or stale template IDs.
- Do not rely on a canvas-only `name` / `desc` pair; the field must also be visible in `变量管理 -> 对话字段`.
- If the variable-list or variable-create endpoint is unknown, inspect the page Network calls or frontend API definitions first. If still unknown, stop and ask for the endpoint or permission to configure through the page.

P0 failure pattern:

```text
智能信息采集已开启，llmNodeCollectParamList 有字段，但变量管理 -> 对话字段为空。
```

This means the collection configuration is not usable for call-detail output, even if `/ivr/updateSceneList` accepted the saved graph.

### Mode 1: Standard Configuration, Preferred

Use this as the default path.

1. In the smart Agent node page, set `智能信息采集` to `采集`.
2. Backend field mapping for that front switch is `llmNodeCollectParamEnabled=1`.
3. Click `添加对话字段`; backend field mapping is `llmNodeCollectParamList`.
4. Select fields from the existing variable library or create new fields in `变量管理 -> 对话字段`.
5. Re-read the variable list and use the returned real positive field IDs in `llmNodeCollectParamList`.
6. For every field, write a concise `desc` / `字段描述` that explains extraction logic and business use.
7. Insert `{collectParam}` once into the prompt, usually under the core task or information-collection section.

Important field distinction:

- Front-page `智能信息采集` = `llmNodeCollectParamEnabled` + `llmNodeCollectParamList`; this controls the radio group users see beside the task prompt and the `{collectParam}` field list.
- Lower-page `信息采集` = `infoCollectEnabled` + `infoCollectConfigList`; this is a separate section with model-analysis field configs and should not be used as the only proof that the visible `智能信息采集` switch is enabled.
- When a user says the visible `智能信息采集` still shows `不采集`, read and patch `llmNodeCollectParamEnabled`, not only `infoCollectEnabled`.

Important:

- Insert `{collectParam}` only once, no matter how many fields are configured.
- The model reads all field definitions from the configured table.
- The main smart-Agent output format can stay as `回复内容{"intent":"当前意图"}`.

Acceptance gate:

- If the page should show `智能信息采集 = 采集`, `llmNodeCollectParamEnabled` must be `1` in all three copies: backend node, `sceneListFrontend.nodeList`, and graph `customData`.
- `变量管理 -> 对话字段` must contain every approved scenario-derived field before the graph references it.
- `llmNodeCollectParamList` must contain the approved scenario-derived fields in all three copies, and every item must reference the same real positive ID returned by the variable list.
- Negative IDs, invented IDs, stale template IDs, or fields missing from variable management are not acceptable.
- `{collectParam}` must appear exactly once in the prompt.
- `infoCollectEnabled=1` alone is not a pass for the visible `智能信息采集` radio group. It only proves the lower `信息采集` section is enabled.
- After changing collection fields, canvas-save validation must pass: the smart Agent drawer can reopen, `智能信息采集=采集` remains visible, fields remain selectable from variable management, and page save/update succeeds. If real click-save is unavailable, simulated page-save validation must be documented with the exact limitation.

Recommended prompt line:

```text
信息采集：从用户原话和当前对话上下文中提取下方对话字段；仅基于明确证据填写，不确定时留空或写“未提及”。{collectParam}
```

### Sequential Qualification Collection Pattern

Use this pattern when the smart Agent's job is not broad sales chat, but ordered qualification or intake collection. Typical examples include loan pre-screening, recruiting intake, appointment qualification, policy confirmation, and any scenario where the field order is part of the business process.

Prompt requirements:

1. State the role boundary: the Agent only performs the approved collection task and does not expand into unrelated business explanation.
2. Declare the exact field order and keep it stable. The Agent must ask one question at a time, must not reorder fields, and must not skip a field unless the user gives a valid skip answer.
3. Define a valid answer for each field. A valid answer is either substantive information for the current question or an explicit skip state such as `跳过` / `不想答` / `不清楚`.
4. Treat interruptions as invalid answers to the current field. User questions, objections, small talk, complaints, asks for explanation, or off-topic answers must be handled briefly, then the Agent returns to the interrupted question.
5. If the user asks why a field is needed, the Agent gives a short purpose explanation, then repeats or rephrases the current question. Do not mark the field complete from the objection itself.
6. If the user gives one answer that clearly covers two adjacent fields, the prompt may define a specific skip rule, such as `没房没车` completing both house and car fields. Do not invent broad skip rules.
7. If the user explicitly skips a field, record the approved skip value and advance. Do not repeatedly pursue that same field.
8. Terminal success / failure criteria must be explicit. For example, success may require all fields, or enough fields for downstream screening; failure may require repeated refusal, complaint, or consecutive silence.

Field description requirements:

```text
字段名：<field name>
字段描述：对应第 <n> 题；仅当用户对当前问题给出 <accepted evidence> 时填写；用户明确跳过 / 不想答 / 不清楚时填写 <skip convention>；未问到或仅有打断/反问/闲聊/解释请求时留空或写“未提及”；不得根据语气、年龄、姓名、职业或上下文自行推测。默认值：<是否允许默认值和条件>。
```

Default values are allowed only when the business prompt explicitly defines them. For example, a consent field may default to `同意` only if the source prompt says unasked or unanswered consent should be treated that way. Sensitive fields, contact fields, identity fields, income, assets, credit, gender, or risk status must not get defaults unless the user explicitly approved that convention.

Output structure:

- Standard mode remains preferred: configure `llmNodeCollectParamList`, insert `{collectParam}` once, and let the platform populate the dialogue-field extraction list.
- If the prompt must control inline values, use natural reply plus one JSON object in the same turn. Do not output Markdown, labels, tables, analysis, or multiple alternatives.
- Terminal examples:

```text
好的，那我先不打扰您了。{"intent":"采集失败"}
这边已经做好登记了，后续工作人员会再联系您。{"intent":"采集成功"}
```

- Inline `param` example, only when custom output control is explicitly required:

```text
好的，我记下了。{"intent":"问询中","param":[{"name":"所在城市","value":"深圳"}]}
```

Hard acceptance checks:

- The prompt contains a fixed field order when the business process needs one.
- The prompt says one turn asks only one collection question.
- The prompt says interruption / objection / explanation request does not complete the current field.
- The prompt says explicit skip values advance without repeated pursuit.
- Terminal JSON, if present, uses valid business intents such as `采集成功` / `采集失败`, not `兜底`.
- Inline `param`, if present, uses field names that exactly match configured dialogue fields.

### Mode 2: Custom Prompt / Inline Param JSON

Use only when the user explicitly wants full prompt control or the backend workflow requires the Agent to output collected fields inline.

Output shape:

```text
回复内容{"intent":"当前意图","param":[{"name":"字段名","value":"字段值"}]}
```

Rules:

- `name` must exactly match configured dialogue field names.
- `value` must come from user wording or clear conversation evidence.
- Use empty string, `未提及`, or a user-approved null convention when no evidence exists.
- Do not invent missing values.
- Do not add explanations outside the JSON.

If a terminal intent maps to a downstream speaking end node, terminal-closing ownership still applies:

```text
好的，我记下了。{"intent":"有意向或同意","param":[{"name":"微信确认状态","value":"已确认"}]}
```

## Field Design Rules

### Dynamic Field Principle

Design the field list from the current scenario. Start from the business decision the caller wants after the call:

- Product demo / B2B lead: company name, demand scenario, current system status, demo interest, contact method.
- Recruitment: city, target role, availability, expected salary, whether willing to add WeChat.
- Property / sales lead: area, budget, location preference, viewing time, contact method.
- Service handling: complaint reason, chosen solution, refund / replacement preference, follow-up time.
- Quality review: identity match status, consent status, whether voice assistant answered.

Do not copy a fixed list from another IVR. Add names, phone numbers, company names, or other PII only when the current prompt and business flow genuinely need them.

For contact follow-up scenarios, do not collapse all contact methods into `客户手机号`. Phone numbers, WeChat IDs, current calling number, and "unwilling to provide" are different outcomes and need explicit fields or status values when the business flow depends on them.

Good fields are:

- action-oriented: `是否同意加微信`, `预约时间`, `处理方案`, `退款方式`
- evidence-friendly: the value can be grounded in something the user said
- stable across calls: not over-specific to one test utterance
- useful for follow-up, reporting, or quality review

Avoid fields that are:

- duplicate of routing intent without extra business value
- impossible to infer from call content
- too broad, such as `客户情况`
- sensitive without business necessity
- dependent on hallucination or business facts not mentioned in the call

Recommended field description shape:

```text
字段名：<short name>
字段描述：仅当用户明确表达 <condition> 时填写 <value convention>；未表达时留空 / 未提及；不得根据语气猜测。
```

### Optional Lead-Collection Field Templates

Use these only when the scenario needs customer identity or follow-up qualification. They are examples, not default fields. Adjust names to match the backend variable library and remove any field that the current prompt does not need.

```text
字段名：客户姓名
字段描述：仅当用户明确说出姓名、称呼或“我叫...”时填写用户姓名或称呼；未表达时留空或写“未提及”；不得从手机号、公司名或语气猜测。

字段名：客户手机号
字段描述：仅当用户明确说出完整手机号或可合并的分段手机号时形成 11 位候选手机号；进入手机号采集中状态后，支持客户分2次、分8次、甚至一位一位慢速报号，并在本次手机号采集会话内持续累积数字片段、中文数字、幺/一/零等号码表达；形成 11 位候选号码后必须先复述核对，客户确认后才填写为已确认手机号；未完整表达或未确认时留空、写“未完整”或“待确认”；不得编造缺失数字，不得把时间、金额、业务量拼入手机号。

字段名：客户微信号
字段描述：仅当用户明确提供微信号且该微信号不是 11 位手机号时填写；支持字母、数字、下划线、短横线等分段表达；必须逐段复述并获得客户确认后才填写为已确认微信号；不得写入手机号字段，不得根据手机号或公司名推测微信号。

字段名：联系方式类型
字段描述：根据用户明确提供或确认的联系方式填写 `手机号`、`微信号`、`本机号码`、`不愿提供`、`待跟进` 或 `未提及`；不得把非手机号微信号归类为手机号。

字段名：联系方式确认状态
字段描述：记录联系方式是否已确认，可填 `待确认`、`已确认`、`客户否认`、`客户纠正中`、`客户拒绝提供`；未经过复述确认的手机号或微信号不得标记为已确认。

字段名：公司名称
字段描述：仅当用户明确说出公司、单位、机构或店铺名称时填写原话中的名称；未表达时留空或写“未提及”；不得把职位、行业或项目名误当作公司名称。
```

### Phone Number Multi-Round Collection

Phone numbers are often split by ASR into multiple user turns, especially when the user speaks slowly or pauses between number groups.

When the scenario collects phone numbers:

- Treat `客户手机号` as a session-based accumulation field, not a single-turn exact-match field.
- In the main prompt, add a `手机号采集中状态` rule: after the Agent asks for a phone number, short digit fragments in the next several user turns should be accumulated instead of treated as failures.
- In `llmNodeCollectParamList.desc`, say that the field supports slow, segmented, multi-round reporting, including 2-part, 8-part, and one-digit-at-a-time reporting.
- If the lower `infoCollectConfigList` model extractor is also configured, set the phone extractor's `recognitionRound` high enough for one-by-one reporting. Use `11` when the flow must tolerate a user speaking one digit per turn.
- Do not force the user to restart after every incomplete fragment. Use continuation prompts such as: `好的，我先听到前面这一段了，您继续往后报就行。`
- Only ask the user to restart when they explicitly say the previous digits were wrong, the accumulated digits exceed 11 and cannot be resolved, or repeated attempts still cannot form a valid number.
- Do not merge time or scheduling expressions into the phone number, such as `六点之前`, `下午三点`, `明天`, or `一会儿`.

### Phone Number Confirmation Gate

Collecting 11 digits is not the end of the phone-number flow. It only creates a candidate number.

Required behavior:

1. If the user only says "记一下我手机号" but has not reported digits, ask them to report the number. Do not say the number has been recorded.
2. When the candidate reaches 11 digits, read it back before any terminal routing, for example: `我跟您核对一下，是 18210235565，对吗？`
3. Only after explicit confirmation such as `对` / `是` / `没错` / `可以`, treat the phone number as confirmed and allow follow-up or terminal `intent` output.
4. If the user says `不对` / `错了` / `重来`, clear the candidate and restart collection.
5. If the user corrects part of the number, update the candidate from the correction, then read back the full 11-digit number again.
6. Before confirmation, do not say `已经记下`, do not promise that a consultant will call this number, and do not output a terminal `intent` solely because 11 digits were heard.

Recommended prompt rule:

```text
手机号确认门：当你在手机号采集中累积出 11 位候选号码后，必须先完整复述给用户核对，例如“我跟您核对一下，是 18210235565，对吗？”只有用户明确确认后，才视为已确认手机号并继续后续收口或意图跳转；如果用户否认、纠正或要求重来，按用户纠正内容更新或清空候选号码，并再次复述核对。未确认前不得说“已经记下”，不得输出终态 intent。
```

### Contact Method And WeChat ID Collection

Do not assume the user's contact method is always a phone number.

Recommended fields when the scenario needs contact follow-up:

- `联系方式类型`: `手机号` / `微信号` / `本机号码` / `不愿提供` / `待跟进` / `未提及`
- `客户手机号`: only confirmed 11-digit mobile numbers
- `客户微信号`: confirmed non-phone WeChat IDs
- `联系方式确认状态`: `待确认` / `已确认` / `客户否认` / `客户纠正中` / `客户拒绝提供`

Rules:

1. If the user says their WeChat is their phone number, run the phone-number confirmation gate and store the confirmed value in `客户手机号`; set `联系方式类型=手机号`.
2. If the user says "微信不是手机号" or provides a non-phone WeChat ID, switch to WeChat-ID collection. Do not validate it as an 11-digit phone number and do not write it into `客户手机号`.
3. A WeChat ID may include letters, digits, underscore, hyphen, or mixed spoken tokens such as "下划线", "横杠", "大写 A", "小写 b". Capture it as a character / segment sequence, not as natural-language intent.
4. Read the WeChat ID back segment-by-segment before treating it as confirmed, for example: `我跟您核对一下，微信号是 a b c 下划线 2026，对吗？`
5. If the user corrects a segment, update that segment and read back the full WeChat ID again.
6. Before confirmation, do not say `已经记下`, do not promise follow-up through that WeChat ID, and do not output a terminal `intent` solely because a candidate WeChat ID was heard.
7. If the user refuses or says "稍后加你", record the status as `待跟进` or `客户拒绝提供`; do not invent a WeChat ID.

Recommended prompt rule:

```text
联系方式采集：不要默认把联系方式等同于手机号。若用户提供 11 位手机号或说微信就是手机号，走手机号确认门；若用户说“微信不是手机号”或提供非手机号微信号，切换到微信号采集，把它记录到“客户微信号”而不是“客户手机号”。微信号可能包含字母、数字、下划线、短横线等，必须按字符或分段复述给用户确认，例如“我跟您核对一下，微信号是 a b c 下划线 2026，对吗？”客户明确确认后，才标记为已确认联系方式；客户纠正时更新后再次完整核对。未确认前不得说“已经记下”，不得输出终态 intent。
```

## Recommended Use Cases

- Lead qualification: interest level, budget, location, property size, appointment time, contact preference.
- Hiring / recruitment calls: city, job interest, availability, expected salary, whether willing to add WeChat.
- Service handling: selected solution, refund choice, complaint reason, replacement preference.
- Education / course calls: grade, subject, pain point, follow-up time, whether accepted materials.
- Quality review: whether user consented, whether identity matched, whether voice assistant answered.

## When Not To Use

- If the only required result is route selection; use `intent` alone.
- If a field cannot be observed from conversation evidence.
- If collecting sensitive personal information is not required for the business flow.
- If the field would encourage the model to ask unnecessary questions and hurt conversion.

## Privacy And Safety

- Minimize personal data. Only collect PII when the user or business workflow explicitly requires it.
- Prefer status fields over raw identifiers, for example `微信已确认` instead of storing a full WeChat ID unless truly needed.
- Do not store phone numbers, ID numbers, addresses, or private identifiers in prompt examples unless explicitly approved.
- Collected values must be evidence-based. Do not infer demographics, income, intent level, or identity from tone alone.

## Interaction With Existing TalkTrack-Agent Rules

### Intent Rules

Information collection does not change intent semantics.

The Agent still outputs the current matched intent / terminal label according to `intent-usage-rules.md`.

### Terminal-Closing Ownership

If the Agent's terminal intent leads to a downstream hangup / end node that speaks, the Agent must use short acknowledgement copy. Information collection may still be emitted via `{collectParam}` or inline `param`, but the Agent must not repeat the downstream closing sentence.

### Prompt Length

Standard `{collectParam}` is preferred because it keeps the prompt shorter. Inline `param` JSON examples can make the prompt longer and should be used sparingly.

### Readback And Audit

When auditing or importing a smart Agent with information collection, verify:

- `变量管理 -> 对话字段` contains every field referenced by the smart Agent collection table.
- Front visible information collection is intentionally enabled or intentionally absent: `llmNodeCollectParamEnabled=1` and `llmNodeCollectParamList` contains the approved fields.
- Every `llmNodeCollectParamList[].id` is a real positive ID from variable-list readback; no negative temporary IDs, guessed IDs, or canvas-only fields are present.
- If the lower `信息采集` section is also used, `infoCollectEnabled` and `infoCollectConfigList` should be checked separately and named separately in reports.
- `{collectParam}` appears exactly once when using standard mode.
- Field descriptions are precise and evidence-based.
- If phone-number collection is configured, the prompt and field description include the phone-number confirmation gate: 11-digit candidate -> readback -> explicit confirmation -> then follow-up / terminal routing.
- If WeChat / contact collection is configured, the prompt and field plan distinguish `联系方式类型`, `客户手机号`, `客户微信号`, and confirmation status; non-phone WeChat IDs are never stored in the phone field.
- Inline `param` JSON, if used, has field names matching configured dialogue fields.
- Intent output format remains valid.
- Terminal-closing ownership remains valid.
- After a write task, the `/script-graph?ivrId=<ivrId>` canvas can open and save/update from the page view, or the report clearly says only simulated canvas-save validation was possible.

## Human Confirmation Required

Ask for confirmation before backend write / import when:

- choosing the list of dialogue fields
- creating new fields in the variable library
- using a variable-management endpoint that has not been verified in the current environment
- collecting PII or sensitive values
- choosing standard `{collectParam}` vs custom inline `param` JSON
- changing an existing prompt's output format from `{"intent":"..."}` to `{"intent":"...","param":[...]}`

## Prompt Package Add-On

When generating a prompt package with information collection, include:

```markdown
## Smart Information Collection Plan
| Field | Description | Value convention | Evidence source | Required? |
| --- | --- | --- | --- | --- |

Recommended mode: Standard `{collectParam}` / Custom inline `param`
Prompt insertion point:
Privacy risk:
Human confirmation needed:
```
