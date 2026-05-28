# Research 03: MDTM Template 02 + Reference Task Example

**Status:** Complete
**Researcher:** researcher-03
**Topic:** Template & Examples — MDTM Template 02 + reference task example
**Date:** 2026-05-27

## Purpose

Document the OUTPUT-task-file shape required by MDTM Template 02 so the rf-task-builder can produce a correct task file for the IronOps builder implementation.

## Sources

1. `/config/workspace/IronClaude/src/superclaude/templates/workflow/02_mdtm_template_complex_task.md` (Template 02)
2. `/config/workspace/IronClaude/src/superclaude/templates/workflow/01_mdtm_template_generic_task.md` (Template 01 — comparison)
3. `/config/workspace/IronClaude/.dev/tasks/to-do/TASK-RF-20260525-194356/TASK-RF-20260525-194356.md` (reference task)

**Template 02 vs Template 01:** Template 01 ends at Section K. **Template 02 adds Section L (Intra-Task Handoff Patterns L1-L7) and Section M (Phase-Gate Composite Patterns M1-M2)**. These are the load-bearing additions that justify using Template 02 for a task with discovery -> build -> test -> review -> aggregate flow.

---

## REQUIREMENTS — Mandatory Features of the Generated Task File

Every requirement is grounded in a Template 02 section ID. The rf-task-builder MUST produce a task file that satisfies ALL of these.

### R1. Frontmatter (Section H, frontmatter block lines 1-44)

The frontmatter MUST be a YAML block at the top of the file containing AT LEAST these fields. The reference task TASK-RF-20260525-194356.md lines 1-52 demonstrate a real-world shape that includes Template 02's required fields PLUS project-specific extensions (`template`, `tracks`, `coordinator`, `autogen_method`).

Required fields (per Template 02 lines 1-44):

- `id: "TASK-[AGENT]-[TASKTYPE]-YYYYMMDD-HHMMSS"` — e.g., `TASK-RF-20260527-153758-ironops-builder` style
- `title: "..."` — clear, action-oriented
- `description: "..."` — what it accomplishes and purpose
- `status: "🟡 To Do"` (or plain `"To Do"` per reference task line 5 convention)
- `type:` — e.g., `"Implementation"` (reference task line 6)
- `priority:` — e.g., `"High"`
- `created_date`, `updated_date` (YYYY-MM-DD)
- `assigned_to:` — e.g., `"rf-task-executor"`
- `autogen: false` (or true if dynamic)
- `coordinator:` — e.g., `"rf-team-lead"` (reference task line 14)
- `parent_task: "..."`
- `depends_on:` — list of dependency IDs
- `related_docs:` — list of `{ path, description }` entries pointing at every research file, governing workflow, spec, PRD/TDD (see reference task lines 18-28)
- `tags:` — list
- **`template_schema_doc:`** — MUST be set to the full absolute path of Template 02. The reference task at line 35 sets it to `/config/workspace/IronClaude/.claude/templates/workflow/02_mdtm_template_complex_task.md`. For an IronOps task building IronOps code while citing IronClaude's template, this field should point at the canonical Template 02 source.
- `task_type: static` (or `dynamic` if items get added during execution — see I6)
- `estimation`, `sprint`, `due_date`, `start_date`, `completion_date`, `blocker_reason`, `ai_model`, `model_settings`, `review_info` (last_reviewed_by, last_review_date, next_review_date) — present even if empty strings

### R2. Top-of-Body Mandatory Sections (Sections D1-D3, ordered)

Strict ordering — **NO checklist items may appear before Phase 1** (D3):

1. `# [Task Title]` (H1 matching frontmatter title)
2. `## Task Overview` — comprehensive description (reference task lines 56-60)
3. `## Key Objectives` — numbered list of concrete outcomes (reference task lines 62-70)
4. `## Prerequisites & Dependencies`
   - `### Parent Task & Dependencies` (parent, blocking deps, what-this-blocks)
   - `### Previous Stage Outputs (MANDATORY INPUTS)` with the literal banner `**INFORMATIONAL ONLY - NO CHECKLIST ITEMS HERE**` and a bulleted list of upstream output paths + purposes (D2 + reference task lines 82-91)
   - `### Handoff File Convention` — describes the `phase-outputs/` subdir layout (`discovery/`, `test-results/`, `reviews/`, `plans/`, `reports/`) (reference task lines 93-106)
   - `### Frontmatter Update Protocol` — restates F5 checkpoints (reference task lines 108-117)
5. (Optional) `## Execution Context` — reader aid summarizing references/source areas/constraints (reference task lines 119-125)
6. `## Detailed Task Instructions` — sole container for `### Phase N: ...` headers

### R3. Phase Structure (Section F + Section L7)

- Phases use `### Phase N: Name` headers (reference task lines 133, 147, 169, 183, 209)
- Steps use `**Step N.M:** Title` bold subheaders WITHOUT checkboxes (E4 — "NEVER place checkboxes next to step numbers")
- Each step contains EXACTLY ONE `- [ ]` checkbox item (the self-contained item)
- Phases flow top-to-bottom; no backward references (E3)
- Phase 1 is ALWAYS `Preparation and Setup` with: Step 1.1 (status update to Doing), Step 1.2 (create phase-outputs handoff dirs), plus optional inventory/discovery prep steps. Reference task Phase 1 (lines 133-145) demonstrates 3 prep steps: status-update, mkdir handoff, build implementation inventory from research.
- Middle phases follow L7 lifecycle patterns: Discovery (L1) -> Build (L2) -> Test (L3) -> Conditional (L5) -> Review (L4) -> Aggregate (L6)
- Phase Gate sections use `### Phase Gate: Quality Verification` or `### Phase N: Task-Integrity QA Gate` (reference task line 209) and follow M1 pattern (aggregate -> QA spawn -> conditional proceed)
- Final user-facing actions live under `## Post-Completion Actions` (NOT inside the phase numbering — see ANTI-ORPHANING below)

### R4. Self-Contained Checklist Items (Section B — CRITICAL)

Per B2, EVERY `- [ ]` item MUST embed all 6 elements as ONE verbose paragraph:

1. **Context Reference with WHY** — what file(s) to read and why
2. **Action with WHY** — what to do
3. **Output Specification** — exact file path, file name, content, template-to-follow
4. **Integrated Verification** — "ensuring..." clause forbidding hallucination
5. **Evidence on Failure Only** — blocker logging instructions (J1 pattern)
6. **Explicit Completion Gate** — "Once done, mark this item as complete."

B3: ONE FULL PARAGRAPH per item. NOT multiple lines, NOT bullets, NOT nested.

### R5. Embedding Rules (Section C — NEVER as separate sections)

- C1: Outputs/deliverables embedded IN items, no separate "Outputs" section
- C2: Success criteria embedded as `ensuring...` clauses, no separate "Success Criteria" section
- C3: Verification embedded in action items, NO separate verification checklist items, NO "Verification Checklist" section
- C4: Task completion handled only by `## Post-Completion Actions`, NO "Task Completion and Handoff Protocol" section

### R6. Checklist Structure Rules (Section E)

- E1: Flat checkboxes only — NO nested `- [ ]` under `- [ ]`
- E1: Use `**Step X.Y:**` bold headers (not checkboxes) for grouping
- E2: Components-FIRST, summary-LAST — any summary checkbox appears at END of a sequence, never before its components
- E3: Sequential top-to-bottom order; no "go back and update" instructions
- E4: NO checkboxes adjacent to step number headers

### R7. Phase-Gate QA Enforcement (Sections I15-I17, M1-M2)

Required when task has 2+ execution phases and later phases depend on earlier phase outputs (per I15). For an IronOps builder task that creates Python code + CI infra, M2's table prescribes:

- After implementation phase: code-modifying task gate
- After task file creation (if building task files): `task-integrity` gate

A phase-gate sequence consists of (M1):

1. **Aggregation item** (L6 pattern) — Glob the phase outputs into a summary report
2. **QA agent spawn item** — spawn `rf-qa` (structural) or `rf-qa-qualitative`, with: agent name, `qa_phase: <gate-type>`, `fix_authorization: true`, ADVERSARIAL STANCE framing (per user's `feedback_rfqa_adversarial_pattern.md` memory), input file paths, output report path, verdict handling, blocker clause
3. **Conditional-proceed item** (L5 pattern) — IF PASS proceed; IF FAIL, run fix cycle per I16 limits (research-gate=3, synthesis-gate=2, report-validation=3, task-integrity=2, any qualitative=3)

The reference task Phase 5 (lines 209-221) is a textbook task-integrity gate with all three M1 items in order.

### R8. Post-Completion Validation (Section I17)

Before frontmatter status flips to Done, MUST verify:

1. All `- [ ]` marked `- [x]` (no skipped items)
2. All specified output files exist on disk (Glob check)
3. All blockers in Task Log have resolution notes
4. If source code modified: relevant tests pass

These items live in `## Post-Completion Actions` BEFORE the frontmatter-update item. Reference task Steps 6.1, 6.2, 6.3, 6.4 (lines 225-239) demonstrate the canonical 4-item Post-Completion sequence: output-audit -> final-validation-evidence -> task-summary -> frontmatter-flip-to-Done.

### R9. Testing Requirements for Code-Modifying Tasks (Section I18)

The IronOps builder task DOES modify source code (creates Python module, CI workflow, installer entry). Therefore I18 applies:

1. Must include at least one testing checklist item
2. Item MUST specify exact test command (e.g., `uv run pytest tests/cli/test_ironops.py -v`)
3. Define pass criteria (e.g., "all tests pass with no regressions")
4. Specify where test results are captured (`phase-outputs/test-results/...`)
5. Follow B2 self-contained pattern

Use the L3 (Test/Execute) pattern for testing items (per I18 last line).

### R10. Task Log / Notes Section (Section G + reference task lines 241-285)

End of file MUST include `## Task Log / Notes` with these subsections:

- `### Task Summary` — placeholder for Post-Completion Step 6.3 to fill
- `### Execution Log` — for timestamped entries
- `### Phase N - <Phase Name> Findings` — ONE PER PHASE, for blocker logging
- `### Post-Completion Findings`
- `### Follow-Up Items Identified`
- `### Deviations from Process`
- `### Blocker Entry Format` — describes the structure agents use when logging blockers

### R11. Handoff File Convention (Section L preamble)

Items write outputs to `<task-dir>/phase-outputs/` with subdirs:

- `discovery/` — L1 outputs
- `test-results/` — L3 outputs (raw + structured summary)
- `reviews/` — L4 verdicts
- `plans/` — L5 conditional outputs (fix plans, verdicts)
- `reports/` — L6 aggregations

For an IronOps builder task at `.dev/tasks/to-do/TASK-RF-20260527-153758-ironops-builder/`, the convention path becomes `.dev/tasks/to-do/TASK-RF-20260527-153758-ironops-builder/phase-outputs/` and Step 1.2 must mkdir all 5 subdirs.

---

## EXEMPLAR — Verbatim B2-Compliant Items from the Reference Task

### Exemplar 1: L1 Discovery + Build inventory (reference task line 145, Phase 1 Step 1.3)

> - [ ] Read the gate-passed research summary at `/config/workspace/IronClaude/.dev/tasks/to-do/TASK-RF-20260525-194356/research-notes.md`, the CLI registration research at `[...]/research/01-cli-registration.md`, the command and skill research at `[...]/research/02-command-skill-patterns.md`, the report and scaffold research at `[...]/research/03-report-scaffold-behavior.md`, and the test and validation research at `[...]/research/04-test-verification.md` to extract the exact implementation files, constraints, test cases, and validation commands for this feature, then create `[...]/phase-outputs/discovery/init-lite-implementation-inventory.md` containing a structured markdown inventory with sections `Source Files To Create`, `Source Files To Modify`, `Tests To Create Or Modify`, `Safety Invariants`, `Validation Commands`, and `Installer Mapping Decision`, ensuring every listed file is backed by the research citations, the inventory names `src/superclaude/cli/init_lite.py` [...] with per-file evidence including `/config/workspace/IronClaude/src/superclaude/cli/main.py:18-26`, [...], no content is fabricated beyond the cited research, and no placeholder text remains. If unable to complete due to missing research files, file access issues, or unclear requirements, log the specific blocker using the templated format in the `### Phase 1 - Preparation and Implementation Inventory Findings` section of the `## Task Log / Notes` at the bottom of this task file, then mark this item complete. Once done, mark this item as complete.

**Why this is exemplary:** Single paragraph. Embeds ALL 6 B2 elements: (1) context with file:line citations, (2) action with reason, (3) exact output path + structured section names, (4) "ensuring every listed file is backed by the research citations [...] no content is fabricated", (5) blocker fallback pointing at exact findings section, (6) "Once done, mark this item as complete."

### Exemplar 2: L3 Test/Execute pattern (reference task line 187, Phase 4 Step 4.1)

> - [ ] Read the test and validation research at `[...]/research/04-test-verification.md`, the behavior tests at `[...]/tests/cli/test_init_lite.py`, and the registration tests at `[...]/tests/cli/test_cli_registration.py` to confirm the required focused test scope, with CLI entry point evidence at `/config/workspace/IronClaude/pyproject.toml:64-66` [...], then use the Bash tool from `/config/workspace/IronClaude` to run `uv run pytest tests/cli/test_init_lite.py tests/cli/test_cli_registration.py -v 2>&1`, write the complete raw output to `[...]/phase-outputs/test-results/focused-cli-pytest-output.txt`, and write `[...]/phase-outputs/test-results/focused-cli-pytest-summary.md` containing overall result, total tests run, pass/fail/error/skip counts, failed test names if any, and the pytest summary line, ensuring the command uses UV exactly, the summary accurately reflects raw output with no fabricated results, and failures are preserved for later remediation. If the command cannot execute due to environment, dependency, or file access issues, log the specific blocker using the templated format in the `### Phase 4 - Run Required Validation Commands and Capture Results Findings` section of the `## Task Log / Notes` at the bottom of this task file, then mark this item complete. Once done, mark this item as complete.

**Why this is exemplary:** L3 dual-output pattern (raw output `.txt` + structured summary `.md`). Specifies tool (Bash), cwd, exact command, both output paths, summary structure.

### Exemplar 3: M1 QA-Gate Spawn (reference task line 217, Phase 5 Step 5.2)

> - [ ] Read the QA input report at `[...]/phase-outputs/reports/implementation-validation-qa-input.md`, the implementation inventory at `[...]/phase-outputs/discovery/init-lite-implementation-inventory.md`, and the validation verdict at `[...]/phase-outputs/plans/validation-verdict.md` to gather the evidence package, then spawn `rf-qa` with `qa_phase: task-integrity`, `fix_authorization: true`, and an explicit `ADVERSARIAL STANCE` instruction to verify the implemented feature against the task constraints, source-of-truth discipline, no target-project mutation invariants, dry-run no-write invariant, default report marker, scaffold opt-in scope, installer protocol mapping, test coverage, and validation command evidence, requiring the QA agent to write its binary PASS/FAIL report to `[...]/phase-outputs/reviews/rf-qa-task-integrity.md`, ensuring the QA prompt includes the exact input files and asks for concrete findings with file/path evidence rather than general approval. If unable to spawn the QA agent or if required input files are missing, log the specific blocker [...] then mark this item complete. Once done, mark this item as complete.

**Why this is exemplary:** Demonstrates the user's `feedback_rfqa_adversarial_pattern.md` memory exactly — pairs `fix_authorization: true` with explicit `ADVERSARIAL STANCE` framing. Specifies exact `qa_phase: task-integrity` label and binary PASS/FAIL output path.

---

## FORBIDDEN PATTERNS (from Template 02 Section B5, lines 164-184)

### F1. Standalone "read context" items that produce no output

```markdown
- [ ] Read file `ib_agent_core.md` and log findings
- [ ] Read file `component-spec.md` for requirements
```

**Why forbidden (B1):** Rigorflow batches across sessions; context loaded in batch 1 will NOT survive to batch 3. A "read and log" item has no actionable output, so the read is wasted — the context is gone before the next item can use it. Always embed the read INSIDE the action item that consumes it.

### F2. Missing context reference (no source of truth)

```markdown
- [ ] Create ApiHandler.ts with proper methods
- [ ] Update the configuration file
```

**Why forbidden:** Which methods? From where? Without a context citation the agent must invent the spec, which is exactly the hallucination Section I9 forbids.

### F3. Multi-line / bulleted checklist items (B5)

```markdown
- [ ] **Context:** Read spec file
      **Action:** Create handler
      **Output:** ApiHandler.ts
```

**Why forbidden (B3):** Items must be ONE FULL PARAGRAPH. Multi-line formatting breaks the "complete prompt that could execute independently" contract.

### F4. Separate verification/confirmation items (B5, C3, I12)

Do NOT add `- [ ] Verify the handler file was created correctly` as a follow-up. Verification belongs INSIDE the action item via the `ensuring...` clause. The QA gate handles cross-batch verification.

### F5. Overly granular items (B5)

`- [ ] Create directory` standing alone is wrong. Combine directory creation with the file creation that needs it.

### F6. Separate REMINDER blocks between items (E4)

Worker agents only see batch items, not surrounding prose. If a reminder is needed, integrate it into the checklist item itself.

### F7. Parent checkbox above child checkboxes (E1, E2)

```markdown
- [ ] Create directory structure:
  - [ ] Create outputs/
  - [ ] Create analysis/
```

**Why forbidden:** Flat structure only. Use a header-without-checkbox for grouping; put a summary checkbox at the END if needed.

### F8. Summary checkbox before its components (E2)

```markdown
- [ ] Create outputs/ directory
- [ ] All directories created   ← WRONG: summary mid-sequence
- [ ] Create analysis/ subdirectory
```

**Why forbidden:** Work flows top-to-bottom; summaries verify completed work, so they must come AFTER.

### F9. Backward references (E3)

"Mark item complete in section above" / "Update the section checklist" / "See checklist below" / "Return to phase and mark complete" — ALL forbidden.

### F10. Cross-phase subagent delegation (F2)

A spawned subagent receives work from a SINGLE checklist item only. Never spawn a subagent for items spanning multiple phases; never delegate the F1 loop itself.

### F11. Skipping phase-gate QA (F2)

Proceeding to the next phase without a passing QA gate is prohibited (I15-I16).

### F12. Skipping post-completion validation (F2)

Both `rf-qa` (structural) and `rf-qa-qualitative` (operational) validation MUST run before status flips to Done (I17).

---

## PHASE-STRUCTURE GUIDANCE — IronOps Builder Task

Based on Template 02 Section L7 lifecycle patterns and the reference task's 5-phase + Post-Completion shape, the IronOps builder task should follow this structure:

### Phase 1: Preparation and Implementation Inventory

- **Step 1.1:** Update status to Doing, set start_date, log Execution Log entry. (Always Step 1.1, per reference line 137.)
- **Step 1.2:** Create handoff directory tree at `<task-dir>/phase-outputs/{discovery,test-results,reviews,plans,reports}/`. (Reference line 141.)
- **Step 1.3:** Build implementation inventory (L1 Discovery) by reading all research files from researchers 01-04, producing `phase-outputs/discovery/ironops-builder-implementation-inventory.md` with sections: `Files To Create`, `Files To Modify`, `Tests To Create`, `CI Workflow Changes`, `Validation Commands`. (Reference line 145.)

### Phase 2: Implement Source Files (Python, command, skill if any, CI)

- One step per major implementation surface. Each step is an L2 Build-from-Discovery item that reads the inventory + research + relevant code-reference evidence (auggie/serena hits) + creates the source file with all behavior embedded in the `ensuring...` clause.
- Example steps for IronOps:
  - **Step 2.1:** Add IronOps Python module/CLI entrypoint
  - **Step 2.2:** Register IronOps in top-level CLI (if applicable)
  - **Step 2.3:** Add CI workflow file (`.github/workflows/ironops.yml` or equivalent)
  - **Step 2.4:** Add any pyproject.toml / installer hooks
  - **Step 2.5:** (Optional) Add `/sc:ironops` thin command + protocol skill source if a slash-command surface is required

### Phase 3: Add Focused Test Coverage

- **Step 3.1:** Unit tests for IronOps core behavior (L2 pattern — read inventory + implemented source, then write test file)
- **Step 3.2:** CLI registration / regression test updates (if applicable, reference line 177)
- **Step 3.3:** Integration / CI workflow tests (defer integration test details to researcher-04's findings)

### Phase 4: Run Required Validation Commands and Capture Results

L3 Test/Execute pattern for each validation command. Each step uses Bash with `2>&1`, writes raw output to `phase-outputs/test-results/<cmd>-output.txt`, writes structured summary to `phase-outputs/test-results/<cmd>-summary.md`. Mandatory commands for IronOps:

- **Step 4.1:** `uv run pytest tests/<ironops-paths>/ -v` (focused unit + CLI tests)
- **Step 4.2:** `uv run pytest tests/integration/<ironops-paths>/ -v` (integration tests if researcher-04 identifies them)
- **Step 4.3:** `make sync-dev` (only if Phase 2 touched skills/agents/commands under `src/superclaude/`)
- **Step 4.4:** `make verify-sync` (paired with 4.3)
- **Step 4.5:** `make lint`
- **Step 4.6:** Assess validation results (L5 conditional) — IF all PASS write `plans/validation-verdict.md` PASS; IF any FAIL run fix cycle per I16 task-integrity=2 limit, then re-verdict.

### Phase 5: Task-Integrity QA Gate (M1 sequence)

- **Step 5.1:** Aggregate (L6) — produce `reports/implementation-validation-qa-input.md` from inventory + validation-verdict
- **Step 5.2:** Spawn rf-qa (M1 item 2) with `qa_phase: task-integrity`, `fix_authorization: true`, ADVERSARIAL STANCE framing, output to `reviews/rf-qa-task-integrity.md`
- **Step 5.3:** Apply verdict (L5 / M1 item 3) — IF PASS write `plans/task-integrity-gate-verdict.md` PASS; IF FAIL run fix-cycle (max 2 per I16) with strict regression/monotonicity halt rules; if unresolved after 2 cycles, HALT and escalate

### Post-Completion Actions (NOT a numbered phase — separate `##` section)

- **Step 6.1:** Output audit (I17 items 1+2) — confirm all `[ ]` -> `[x]` and all output files exist via Glob; produce `reports/post-completion-output-audit.md`
- **Step 6.2:** Final validation evidence (I17 item 4) — confirm test/lint/sync still PASS; produce `reports/final-validation-evidence.md`
- **Step 6.3:** Fill in `### Task Summary` section in Task Log / Notes
- **Step 6.4:** Update frontmatter `status: Done`, `completion_date`, `updated_date`; log Execution Log completion entry

---

## ANTI-ORPHANING — Task Completion Items MUST Be Inside Final Section

### The rule (Section J, C4, I13)

**Task-completion items live ONLY in `## Post-Completion Actions`, which is a top-level `##` section appearing AFTER all numbered `### Phase N` sections and BEFORE the `## Task Log / Notes` section.**

The reference task structure (lines 209-285) demonstrates the correct ordering:

```
### Phase 5: Task-Integrity QA Gate          (line 209) — last numbered phase
  **Step 5.1:** ... **Step 5.2:** ... **Step 5.3:** ...
## Post-Completion Actions                    (line 223) — top-level ##
  **Step 6.1:** ... **Step 6.2:** ... **Step 6.3:** ... **Step 6.4:** ...
## Task Log / Notes                           (line 241)
  ### Task Summary
  ### Execution Log
  ### Phase 1 - ... Findings
  ### Phase 2 - ... Findings
  ...
```

### Why this matters — the orphaning failure mode

If the frontmatter-flip-to-Done item is placed at the bottom of `### Phase 5` (or any numbered phase) instead of inside `## Post-Completion Actions`:

1. The Phase 5 QA gate verdict has not yet been incorporated into a separate final-check sequence.
2. The post-completion validation (I17) — verify all `[ ]` are `[x]`, all output files exist, all blockers resolved — gets skipped entirely.
3. The task summary section never gets filled in because the agent thinks the task is complete.
4. The status flip happens BEFORE the agent has actually confirmed the work is in a clean, evidenced state.

### Explicit forbidden pattern

```markdown
### Phase 5: Final Phase Name
**Step 5.1:** ...
- [ ] Do the last work item

**Step 5.2:** Mark task complete
- [ ] Update frontmatter to Done   ← ORPHANED — should be in ## Post-Completion
```

### The correct pattern

```markdown
### Phase 5: <last work phase>
**Step 5.N:** <last work step>
- [ ] <last work item with full B2 body>

## Post-Completion Actions

**Step 6.1:** Verify all outputs exist and items complete
- [ ] <I17 item 1+2: Glob check all output files exist + all [ ] are [x]; write reports/post-completion-output-audit.md>

**Step 6.2:** Confirm validation evidence still passes
- [ ] <I17 item 4: read all validation summaries, confirm PASS; write reports/final-validation-evidence.md>

**Step 6.3:** Fill in Task Summary
- [ ] <Read post-completion audit + final validation evidence; populate ### Task Summary in Task Log / Notes>

**Step 6.4:** Mark task complete
- [ ] <Update frontmatter status to Done + completion_date + updated_date; add Execution Log completion entry>
```

### How the rf-task-builder enforces this

When producing the IronOps builder task file, the rf-task-builder MUST:

1. Place the QA gate as the LAST numbered phase (`### Phase 5: Task-Integrity QA Gate`)
2. Open a new top-level `## Post-Completion Actions` heading AFTER the last numbered phase
3. Place all 4 completion items (output-audit, final-validation, task-summary, frontmatter-flip) inside that section
4. Never inline the frontmatter-flip item into a numbered phase

---

## Summary

Template 02 produces a task file with a tightly constrained shape: frontmatter -> top-of-body informational sections (Overview, Objectives, Prerequisites including Previous Stage Outputs + Handoff Convention) -> numbered Phases (each step = one verbose self-contained B2 paragraph with all 6 elements embedded) -> Phase-Gate QA sequences at appropriate boundaries (M1) -> a separate top-level `## Post-Completion Actions` section holding I17 validation items -> `## Task Log / Notes` with per-phase findings subsections.

For the IronOps builder task specifically:

- Use 5 numbered phases: Prep+Inventory -> Implement -> Tests -> Validation -> Task-Integrity QA Gate
- Add Post-Completion Actions section with 4 items (output-audit, final-validation, task-summary, frontmatter-flip)
- Each implementation step is an L2 Build-from-Discovery item citing researcher 01/02/04 outputs + concrete file:line evidence
- Each validation step is an L3 Test/Execute item with dual output (raw .txt + structured .md summary)
- Phase 5 follows M1 strictly (aggregate -> spawn rf-qa with `qa_phase: task-integrity` + `fix_authorization: true` + ADVERSARIAL STANCE -> conditional verdict with fix-cycle max=2)
- All anti-hallucination + source-of-truth + UV-only + no-`.claude/`-staging rules from CLAUDE.md must appear as `ensuring...` clauses in the relevant items
- `template_schema_doc` frontmatter field points at `/config/workspace/IronClaude/src/superclaude/templates/workflow/02_mdtm_template_complex_task.md`
- The reference task TASK-RF-20260525-194356.md is the gold-standard exemplar — pattern-match it section-by-section

