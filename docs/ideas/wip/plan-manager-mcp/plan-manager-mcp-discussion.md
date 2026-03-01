# Plan Manager MCP - Discussion

## Classification

**C. Platform/infrastructure capability**

**Rationale:** This is a development tooling component that extends the existing workflow automation system. The MCP server provides Claude with programmatic access to manipulate plan files, which are central to the project's steel-thread development workflow. It's not user-facing in the traditional sense, not a POC (the plan file format is already established), and not educational.

## Questions and Answers

### Q1: Should the MCP server expose read/query operations in addition to the four write operations?

Options presented:
- A. Write operations only -- Claude can already read files natively
- B. Add read operations too -- structured queries would be more reliable than Claude parsing raw markdown
- C. Start with write-only, design so read operations can be added later

**Answer: B** - Include read operations. Structured queries (list threads, get next uncompleted task, etc.) will be more reliable than having Claude parse raw markdown.

### Context: Plugin Architecture

The project is a Claude Code plugin (`.claude-plugin/plugin.json`). The MCP server should be registered in the plugin manifest so it is automatically available to any project that installs the `idea-to-code` plugin. The plugin already includes skills, commands, and hooks (Node.js-based).

### Q2: What implementation language for the MCP server?

Options presented:
- A. Python with the official `mcp` Python SDK (aligns with workflow scripts, existing pytest infrastructure)
- B. TypeScript/Node.js (aligns with existing plugin hooks, simpler dependency story for a JS-based plugin)
- C. Something else

**Answer: A** - Python with the official `mcp` Python SDK. Aligns with existing workflow scripts and pytest infrastructure.

### Q3: Should there be a step-level mark-complete operation in addition to task-level?

Options presented:
- A. Task-level only -- mark the task and all its steps complete at once
- B. Both task-level and step-level -- allow marking individual steps as Claude progresses
- C. Step-level only -- marking the last step automatically completes the task

**Answer: B** - Both task-level and step-level operations. Claude can mark individual steps complete as it progresses through them, and also mark an entire task complete at once.

### Q4: What level of detail should the insert-thread operation accept?

Options presented:
- A. Only thread title and empty task list -- Claude fills in details later
- B. Fully structured thread -- title, introduction, and complete task definitions including all metadata (TaskType, Entrypoint, Observable, Evidence, Steps)
- C. Title, introduction, and minimal tasks -- metadata fields optional

**Answer: B** - Accept fully structured threads. The insert operation takes a complete thread definition including title, introduction, and full task metadata (TaskType, Entrypoint, Observable, Evidence, Steps).

### Q5: Which specific read operations should the MCP server expose?

Options presented:
- A. All four: list threads, get thread details, get next uncompleted task, get plan summary
- B. Just list threads + next uncompleted task
- C. All four plus additional ones

**Answer: A** - All four read operations:
1. **List threads** - all threads with numbers, titles, and completion status
2. **Get thread details** - a specific thread's full content (introduction, tasks, steps, metadata)
3. **Get next uncompleted task** - first uncompleted task across the plan
4. **Get plan summary** - overview, idea type, and overall progress

### Q6: Are additional write operations needed beyond the original five?

Options presented:
- A. Current five are sufficient (fix numbering, insert thread before/after, mark task/step complete)
- B. Add some additional operations
- C. Add all: delete thread, update/replace thread, insert task, delete task

**Answer: C** - Add all additional write operations. The full write operation set is:
1. **Fix numbering** - renumber threads and tasks after edits
2. **Insert thread before** - insert a fully structured thread before a specified thread
3. **Insert thread after** - insert a fully structured thread after a specified thread
4. **Mark task complete** - mark a task and all its steps as complete
5. **Mark step complete** - mark an individual step as complete
6. **Delete thread** - remove a thread entirely
7. **Update/replace thread** - modify an existing thread's content
8. **Insert task** - add a new task to an existing thread
9. **Delete task** - remove a task from a thread

### Q7: Should fix-numbering be automatic after structural mutations or explicit?

Options presented:
- A. Auto-renumber after every structural mutation
- B. Explicit only -- Claude calls fix-numbering when needed
- C. Both -- auto-renumber by default with option to suppress

**Answer: Both, but differently scoped.** Auto-renumber is applied transparently after every MCP structural mutation (insert/delete thread, insert/delete task). The explicit fix-numbering operation remains available for correcting numbering after *arbitrary edits* made outside the MCP server (e.g., Claude editing the plan file directly via normal file editing).

### Q8: Should the MCP server share parsing logic with `implement_with_worktree.py`?

Options presented:
- A. Fully independent -- own parser, no shared code. Simpler to develop and deploy.
- B. Extract shared parsing into a common library used by both.
- C. Build independently now, refactor to share later.

**Answer: A** - Fully independent. The MCP server has its own parser with no shared code or coupling to `implement_with_worktree.py`. Keeps development and deployment simple.

### Q9: How should insert-task position be specified within a thread?

Options presented:
- A. Insert before a specified task number
- B. Insert after a specified task number
- C. Both before and after, mirroring thread insertion operations
- D. Always append at the end

**Answer: C** - Both insert-task-before and insert-task-after, consistent with the thread insertion pattern.

### Q10: What should update/replace thread accept?

Options presented:
- A. Full replacement -- takes a complete thread definition and replaces entirely
- B. Partial update -- allows updating individual fields
- C. Full replacement for thread, plus a separate "update task" operation

**Answer: A** - Full replacement. Keep it simple. To modify a task within a thread, get the thread details, modify, and replace the whole thread.

### Q11: Change history requirement (user-provided)

All write/mutation operations should accept a **rationale** argument. The rationale is appended to a change history section in the plan file, providing an audit trail of why changes were made. This applies to: insert/delete thread, insert/delete task, replace thread, mark task/step complete. (Fix numbering is mechanical and likely doesn't need a rationale.)

### Q12: Should the MCP server use `uv` to run?

**Answer: Yes.** Use `uv run` with PEP 723 inline script metadata. The server script declares its dependencies (e.g., `mcp` SDK) inline, and the plugin manifest invokes it via `uv run path/to/server.py`. No separate venv or `_python_helper.sh` setup needed. Prerequisite: `uv` must be installed on the host.

