I have an idea for some software I want to develop.

The goal is to:

- Brainstorm and refine the idea.
- Classify the type of work (user-facing feature, architecture POC, platform capability, or example).
- Capture enough detail to later generate the right kind of specification and a steel-thread implementation plan.

Use the following files:

- idea-file: @${IDEA_FILE}
- discussion-file: @${DISCUSSION_FILE}

Your tasks:

1. Help me refine the idea.
2. Classify the idea as one of:
   A. User-facing feature
   B. Architecture POC (validating a critical architectural concern)
   C. Platform/infrastructure capability
   D. Educational/example repository

3. Save:
   - The refined idea in the idea-file.
   - All questions and my answers in the discussion-file.
   - The classification and rationale in the discussion-file as well.

Important constraints:
- In this step, you MUST NOT generate any specification.
- In this step, you MUST NOT generate any implementation or steel-thread plan.
- Your role in this step is to ask questions, refine the idea, and record the discussion.

Process:

- If the discussion file already exists, read it first to understand what has already been covered.
- Ask me one question at a time so we can develop a thorough, step-by-step understanding of the idea.
- Each question should build on my previous answers.
- Define sensible and easily changeable default assumptions so we can focus on the most important aspects.
- If there are multiple options for a question, list them as A, B, C, D, and I will choose one.
- Continue until you believe you have enough information to create a developer-ready specification and a steel-thread-ready plan.

Remember: only one question at a time.

- Continue until you believe you have enough information to later create a developer-ready specification and a steel-thread-ready plan (in subsequent steps, not in this one).
- When you believe all relevant details have been gathered, do NOT generate the specification.
  Instead, ask me:
  "Are there any additional requirements or concerns before we move to the next step (creating the detailed specification)?"
- After asking this question and recording my answer in the discussion-file, STOP. Do not generate the specification or a plan in Step 1.

Remember: this is for questions, clarification, and recording information only. Specification and planning happen in later steps.
