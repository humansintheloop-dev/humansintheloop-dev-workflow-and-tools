# Brainstorm: AskUserQuestion Tool — Discussion

## Q1: What problem motivates this change?

**Question:** What problem are you experiencing with the current interactive approach that motivates switching to the AskUserQuestion tool?

**Answer:** Two issues:
1. Some questions are not asked in multi-choice format, which means responding is more complicated.
2. AskUserQuestion has a better UX.

**Derived conclusion:** The brainstorm already runs as an interactive Claude CLI session (`subprocess.run(["claude", ...])`) which has access to the AskUserQuestion tool. The change is primarily about updating the brainstorm prompt template to instruct Claude to use AskUserQuestion for each clarifying question, ensuring structured multi-choice options are presented.

## Q2: Scope of change

**Question:** Is the scope limited to updating the prompt template, or does it also involve Python code changes?

**Answer:** Prompt-only change. The brainstorm is inherently interactive — no Python code changes needed. Just update the `brainstorm-idea.md` template to instruct Claude to use AskUserQuestion with multi-choice options.

## Q3: When to use AskUserQuestion

**Question:** Should every brainstorm question use AskUserQuestion, or only multi-choice questions?

**Answer:** Two rules:
1. The prompt should strive to ask multi-choice questions unless that's not possible.
2. AskUserQuestion should be used for multi-choice questions.

**Derived conclusion:** For truly open-ended questions where no reasonable options can be offered, fall back to regular text output. AskUserQuestion requires at least 2 options but always provides an "Other" free-text option automatically. It also supports multi-select and preview capabilities.

## Q4: Which prompt to change

**Question:** Should the change apply to both the i2code template and this conversation's prompt, or just the i2code template?

**Answer:** Only the i2code template (`src/i2code/prompt-templates/brainstorm-idea.md`).

## Q5: AskUserQuestion feature usage

**Question:** Should the prompt instruct Claude to use advanced AskUserQuestion features (multi-select, preview)?

**Answer:** Use whatever features make sense for the nature of the question. Don't force it — if a question doesn't fit AskUserQuestion's constraints (e.g., needs more than 4 options), use regular text output instead.

**Derived conclusion:** AskUserQuestion supports 2-4 options max. The prompt should instruct Claude to:
- Prefer multi-choice questions (2-4 options) and use AskUserQuestion for those
- Use multi-select when choices aren't mutually exclusive
- Use preview when comparing concrete artifacts (code, config, mockups)
- Fall back to text output when the question genuinely needs more than 4 options or is fully open-ended

## Q6: Ready to proceed?

**Question:** Are there any additional requirements or concerns before we move to the next step (creating the detailed specification)?

**Answer:** Ready to proceed.

## Classification

**Type: A. User-facing feature**

**Rationale:** This is a UX improvement to an existing user-facing command (`i2code brainstorm`). It changes how the tool interacts with the user by using a structured question UI instead of free-text questions. No architectural changes, no new infrastructure — just a prompt template update that improves the brainstorm experience.
