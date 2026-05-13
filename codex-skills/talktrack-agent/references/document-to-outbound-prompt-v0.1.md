# Document To Outbound Prompt v0.1

Use this reference when the user provides any source material and asks to turn it into a Shandian outbound-call smart-Agent prompt.

The source can be any business document, including ordinary-node scripts, product introductions, project brochures, sales SOPs, FAQs, customer-service policies, pricing sheets, training manuals, resumes, job descriptions, meeting notes, call transcripts, or mixed Markdown / Word / PDF / spreadsheet material.

Do not limit this workflow to hiring or resume scenarios. A resume is only one possible source document type.

## Hard Boundary

- This mode generates a prompt draft or prompt package only.
- Do not write the generated prompt into the backend unless the user separately approves a `prompt-import` task and provides the target IVR / smart node scope.
- Do not invent facts that are not supported by the source material. Mark missing facts as assumptions or open questions.
- Do not copy large source files or full extracted raw text into Obsidian. Keep large source artifacts at their original path and record only paths / summaries when a report is requested.
- Redact or summarize sensitive personal information unless the user explicitly says the exact information is required in the prompt.

## Supported Source Handling

Choose the lightest reliable extraction method for the file type:

- Markdown / TXT: read as UTF-8 text.
- DOCX / PDF: extract text first; use OCR only when the file is image-only or text extraction fails.
- XLSX / CSV: identify sheets / columns, then extract business facts, FAQ rows, pricing rows, or routing rules.
- Mixed folders: build an input inventory first, then process by document type.
- Screenshots / images: use image understanding only for visible text or layout that cannot be extracted otherwise.

Keep source evidence structured:

- `sourcePaths`: original file paths.
- `sourceType`: ordinary-node script, product doc, FAQ, resume, policy, transcript, spreadsheet, mixed, or unknown.
- `extractedFacts`: facts supported by the source.
- `openQuestions`: missing fields needed for a strong outbound call prompt.
- `privacyRisks`: personal or sensitive information found in the source.

## Conversion Steps

1. Classify the source document type and outbound-call goal.
2. Extract factual material: product / service, target user, offer, constraints, differentiators, required questions, forbidden claims, and handoff / termination rules.
3. Identify conversation structure:
   - opening
   - identity / context confirmation
   - need discovery
   - core pitch or explanation
   - objection handling
   - qualification or next-step collection
   - closing / hangup handling
4. Identify intent labels if the target prompt should emit `{"intent":"..."}`.
5. If intent output is required, load `intent-usage-rules.md` and keep hangup / terminal labels compliant.
6. Draft the outbound smart-Agent prompt.
7. Review for grounding, privacy, intent rules, length, and import readiness.
8. Output a prompt package. Do not import it automatically.

## Prompt Package Output

Generate Markdown with these sections:

```markdown
# Outbound Smart-Agent Prompt Draft

## Source Summary
- Source paths:
- Source type:
- Outbound goal:
- Target audience:
- Supported facts:
- Open questions:
- Privacy handling:

## Prompt Draft
<full prompt draft>

## Suggested Intent / Port Plan
| Intent | Meaning | Suggested Target | Notes |
| --- | --- | --- | --- |

## Import Readiness Check
- Factual grounding:
- Privacy risk:
- Intent-rule compliance:
- Estimated length:
- Backend import readiness:

## Human Review Required
- Items requiring business confirmation:
- Items not found in source:
- Risky claims to avoid:
```

## Prompt Draft Requirements

The generated prompt should include:

- Role: the smart Agent's identity and allowed speaking style.
- Goal: the business outcome of the outbound call.
- Audience: who is being called and why.
- Source facts: only facts supported by the source document or explicitly marked assumptions.
- Conversation policy: concise, natural, interruption-friendly, no unsupported promises.
- Flow: opening, probing, explanation, objection handling, next step, closing.
- Safety / compliance: privacy handling, forbidden claims, escalation rules.
- Knowledge boundaries: what to say when the answer is unknown.
- Intent output rules when needed.
- Hangup / terminal handling when needed.

## Ordinary-Node Source Conversion

When the source is ordinary-node content:

- Preserve the business meaning and proven wording, but do not blindly concatenate all node text into one large prompt.
- Convert node-by-node scripts into a flexible dialogue policy: goals, branches, user states, objection types, and next-step criteria.
- Keep short deterministic trigger words as notes for `talktrack-master` if the task is ordinary-node optimization.
- Use `talktrack-agent` only when the target is a smart-Agent prompt or smart-node import package.

## Privacy Rules

For resumes, customer files, call transcripts, or any personal-data-heavy source:

- Do not include phone numbers, email addresses, ID numbers, home addresses, or private identifiers in the prompt unless explicitly required.
- Prefer role / profile summaries over full personal history.
- If the outbound use case genuinely needs personal context, include the minimum necessary context and flag it for human review.

## Review Checklist

Before calling the prompt package ready:

- Does every important claim trace back to source material?
- Are unsupported assumptions listed separately?
- Is the call goal explicit?
- Does the prompt tell the Agent what to do when the user interrupts, refuses, asks for details, or wants a human?
- If intent JSON is required, does it follow `intent-usage-rules.md`?
- Is the generated prompt likely under the backend practical length limit?
- Are sensitive fields removed or minimized?
- Is backend import still a separate approval step?
