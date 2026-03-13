# Session Recording Feature - Technical Specification

## Overview

Automatically record all Claude Code interactions (prompts, responses, and tool calls) to markdown files for later review and reference.

## Core Requirements

### 1. What to Record

Record the following for each session:
- User prompts (everything the user types)
- Claude's responses (full text responses)
- Tool calls with minimal details:
  - Tool name
  - Key parameters (e.g., file paths, commands)
  - Format: `Read file.txt`, `Bash: npm install`, `Edit config.json`

### 2. Storage

- **Location**: `.claude/sessions/` directory in the current workspace
- **File naming**: `session-YYYY-MM-DD-HHMMSS.md` (timestamp-based)
- **Format**: Markdown (.md)
- **One file per**: Conversation thread (new file when user starts fresh with Claude Code)
- **Retention**: Keep all sessions forever (no automatic cleanup)
- **Git**: Don't modify .gitignore (user decides whether to track sessions)

### 3. Recording Behavior

- **Always on**: Automatically record every Claude Code session
- **No user action required**: Zero configuration, works out of the box
- **Incremental writes**: Append to session file continuously as conversation progresses
  - Write after each user message
  - Write after each Claude response
  - Write after each tool call
- **Error handling**: Silent failure - if recording fails, log to debug console but continue session without interruption

### 4. File Format

#### Header (minimal metadata)
```markdown
# Session: YYYY-MM-DD HH:MM:SS

```

#### Message Format
Use markdown formatting with blockquotes:

```markdown
**User:**
> User's prompt text here

**Claude:**
> Claude's response text here
> Can span multiple lines

**Tools Used:**
- Read src/file.ts
- Bash: npm test
- Edit package.json

**User:**
> Next user prompt
```

#### Specific formatting rules:
- User messages: Plain text in blockquote
- Claude responses: Plain text in blockquote
- Tool calls: Bulleted list with minimal format `ToolName parameter` or `ToolName: command`
- Separate each exchange with blank line for readability

### 5. Implementation Architecture

**Type**: Claude Code Plugin (enhance existing plugin in this repository)

**Hooks to use**:
1. **UserPromptSubmit** - Capture user prompts in real-time
2. **PostToolUse** - Capture tool calls after execution
3. **Transcript reading** - Read transcript_path to get Claude's responses

**Implementation files**:
- Hook handler script (bash or node.js) to process hook events
- Session file writer to append to markdown files
- Integration with existing `.claude-plugin/plugin.json`

### 6. Technical Details

#### Session Lifecycle
1. **SessionStart**: Create new session file with timestamp header
2. **UserPromptSubmit**: Append user prompt to file
3. **Transcript read**: Parse latest Claude response and append
4. **PostToolUse**: Append tool call summary
5. **Repeat steps 2-4** for entire conversation
6. **SessionEnd**: Close file (no special footer needed)

#### File Operations
- Use append mode for all writes
- Create `.claude/sessions/` directory if it doesn't exist
- Handle concurrent access gracefully (unlikely but possible)
- Flush after each write for crash safety

#### Tool Call Formatting
Extract minimal info from PostToolUse hook:
- `tool_name`: The tool that was called
- `tool_input`: Parse for key info (file paths, commands, etc.)

Examples:
- `Read` → "Read {file_path}"
- `Edit` → "Edit {file_path}"
- `Bash` → "Bash: {command}"
- `Write` → "Write {file_path}"
- `Grep` → "Grep '{pattern}'"
- `Glob` → "Glob '{pattern}'"

#### Transcript Parsing
- Hook handlers receive `transcript_path` in JSON input
- Read transcript file to extract Claude's latest response
- Track last read position to avoid re-processing
- Handle incomplete responses gracefully (mid-generation)

### 7. Error Scenarios

All errors should be handled silently:
- Cannot create `.claude/sessions/` directory → log, continue
- Cannot write to session file → log, continue
- Cannot read transcript → log, continue
- Malformed hook input → log, continue
- Hook script crashes → Claude Code continues normally

### 8. Non-Requirements (Explicitly Out of Scope)

- No configuration options
- No built-in viewer/search commands
- No automatic cleanup/retention policies
- No .gitignore modifications
- No prompt for user confirmation/setup
- No detailed tool outputs (only summaries)
- No system messages or metadata beyond timestamp

## Implementation Checklist

- [ ] Create hook handler script for UserPromptSubmit
- [ ] Create hook handler script for PostToolUse
- [ ] Implement session file creation with timestamp
- [ ] Implement incremental append logic
- [ ] Implement transcript parsing to extract Claude responses
- [ ] Add tool call formatter (minimal format)
- [ ] Configure hooks in plugin settings
- [ ] Test with various conversation scenarios
- [ ] Test error handling (permission errors, disk full, etc.)
- [ ] Verify markdown formatting in various viewers
- [ ] Document behavior in plugin README

## Example Session File

```markdown
# Session: 2025-11-23 14:30:22

**User:**
> Help me add a new feature to my app

**Claude:**
> I'd be happy to help! Let me first understand your current app structure.

**Tools Used:**
- Read package.json
- Glob src/**/*.ts

**Claude:**
> I can see you're using TypeScript with React. What feature would you like to add?

**User:**
> Add a dark mode toggle

**Claude:**
> Great! I'll help you implement dark mode. Let me check your current styling setup.

**Tools Used:**
- Read src/App.tsx
- Grep 'theme' --type ts

**Claude:**
> I'll create a theme context and add the toggle component.

**Tools Used:**
- Write src/context/ThemeContext.tsx
- Edit src/App.tsx

**Claude:**
> Done! I've added the theme context and integrated it into your app.
```

## Success Criteria

✅ Sessions are automatically recorded without user action
✅ All prompts, responses, and tool calls are captured
✅ Session files are readable markdown
✅ Recording never interrupts or slows down Claude Code
✅ Files are saved to `.claude/sessions/` with timestamp names
✅ Works reliably even if errors occur during recording
✅ Can review sessions with any text editor or markdown viewer
