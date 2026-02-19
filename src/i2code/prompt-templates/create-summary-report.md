# Create Daily Summary Report

Create a markdown summary report for Claude sessions and issues from today.

## Project

$PROJECT_NAME

## Today's Session Files

$SESSION_FILES

## Today's Issue Files

$ISSUE_FILES

## Instructions

Use subagents to process files in parallel, then aggregate the results.

### Step 1: Spawn Subagents

For each session file, spawn a subagent with this prompt:
```
Read and summarize this Claude session file: [FILE_PATH]

Report back with:
- Main task/goal of the session
- Key actions taken (tools used, files modified)
- Outcome (completed, blocked, in progress)
- Any notable user corrections or feedback
- Key learnings or issues encountered

Keep your summary concise (5-10 bullet points max).
```

For each issue file, spawn a subagent with this prompt:
```
Read and summarize this issue file: [FILE_PATH]

Report back with:
- Issue title
- Category (improvement, bug, workflow, etc.)
- Brief description of the problem
- Root cause (if identified)
- Suggested improvement (if any)

Keep your summary to 3-5 bullet points.
```

Run all subagents in parallel using the Task tool with `run_in_background: true`, then collect results with TaskOutput.

### Step 2: Aggregate Results

Once all subagents report back, create a summary report with these sections:

1. **Overview**: Brief summary of the day's work (2-3 sentences)

2. **Sessions Summary**: Compile subagent reports for each session

3. **Issues Filed**: Compile subagent reports for each issue

4. **Patterns & Insights**: Analyze across all results for:
   - Recurring themes
   - Lessons learned
   - Areas for improvement
   - Common categories of issues

5. **Metrics**:
   - Total sessions: X
   - Total issues filed: X
   - Tasks completed vs blocked vs in progress

Format the report in clean markdown suitable for archival and review.
