# Session Recording Feature Implementation Plan

## Overview
This plan implements automatic session recording for Claude Code using the Steel Thread methodology. Each thread delivers a narrow, end-to-end flow that provides immediate value by capturing user interactions with Claude Code in markdown files.

## Instructions for Coding Agent
- Mark each checkbox with '[x]' when the task or step is completed
- Run tests after implementing each feature
- Refactor as needed while keeping tests passing
- Create commits after each successful thread completion

## Steel Thread 1: Basic Hook Infrastructure and Session File Creation

### Purpose
Set up the foundational hook handler infrastructure and implement basic session file creation with timestamp headers.

### Implementation Steps

```text
[x] Create hook handler directory structure
    [x] Create hooks/ directory at top level
    [x] Set up proper directory permissions
    [x] Verify directory is accessible for writing

[x] Write test for session file creation
    [x] Test .claude/sessions/ directory is created if missing
    [x] Test session file has correct timestamp format
    [x] Test session file has correct header format
    [x] Test file permissions allow reading and writing

[x] Implement session file creator (Node.js script)
    [x] Create hooks/session-recorder.js
    [x] Add function to create .claude/sessions/ directory
    [x] Add function to generate session filename with timestamp (session-YYYY-MM-DD-HHMMSS.md)
    [x] Add function to create session file with header "# Session: YYYY-MM-DD HH:MM:SS"
    [x] Add error handling for file system operations

[x] Write test for session lifecycle
    [x] Test new session file created on first write
    [x] Test existing session file is reused during same conversation
    [x] Test session detection logic

[x] Implement session tracking
    [x] Add logic to detect if session file exists for current conversation
    [x] Store session filename in memory for reuse
    [x] Handle session initialization on first user prompt

[x] Refactor and ensure clean code structure
    [x] Extract reusable functions (createDirectory, generateFilename, etc.)
    [x] Add proper error logging to console.error
    [x] Add JSDoc comments for functions
```

**Prompt for Coding Agent:**
```text
Create the basic session recording infrastructure:

1. Create a Node.js script at hooks/session-recorder.js that will handle session recording
2. Implement functions to:
   - Create .claude/sessions/ directory if it doesn't exist
   - Generate session filenames with timestamp format: session-YYYY-MM-DD-HHMMSS.md
   - Create session files with header: "# Session: YYYY-MM-DD HH:MM:SS"
   - Track current session file to avoid creating multiple files per conversation

3. Use TDD approach:
   - Write tests first (can use a simple test runner or manual testing)
   - Implement minimal code to pass tests
   - Refactor for code quality

4. Error handling requirements:
   - All file system errors should be caught and logged to console.error
   - Script should never throw unhandled errors
   - Failed operations should not crash Claude Code

5. When complete, mark all checkboxes with [x] and test manually by creating a session file
```

## Steel Thread 2: UserPromptSubmit Hook Integration

### Purpose
Capture user prompts in real-time and append them to the session file in markdown format.

### Implementation Steps

```text
[x] Write test for UserPromptSubmit hook
    [x] Test hook receives correct JSON input with prompt text
    [x] Test prompt is properly formatted in markdown blockquote
    [x] Test prompt is appended to existing session file
    [x] Test empty prompts are handled gracefully

[x] Implement prompt capture logic
    [x] Read JSON input from stdin in hook handler
    [x] Extract user prompt text from hook data
    [x] Format prompt as markdown: "**User:**\n> {prompt text}"
    [x] Add blank line after prompt for readability

[x] Write test for file append operation
    [x] Test append mode doesn't overwrite existing content
    [x] Test multiple prompts are appended sequentially
    [x] Test file handle is properly closed after write
    [x] Test write operation is flushed for crash safety

[x] Implement session file append
    [x] Use fs.appendFileSync or fs.appendFile for atomic writes
    [x] Ensure data is flushed to disk
    [x] Handle concurrent access gracefully
    [x] Log errors without throwing

[x] Configure UserPromptSubmit hook in plugin.json
    [x] Add "hooks" configuration section
    [x] Register UserPromptSubmit hook pointing to hooks/session-recorder.js
    [x] Test hook is triggered on user input

[x] Write integration test
    [x] Test complete flow: user input -> hook triggered -> file written
    [x] Test session file contains correctly formatted prompt
    [x] Test multiple prompts in sequence
```

**Prompt for Coding Agent:**
```text
Implement UserPromptSubmit hook to capture user prompts:

1. Update session-recorder.js to:
   - Read JSON input from stdin (hook data contains the user prompt)
   - Parse the JSON to extract user prompt text
   - Format as markdown: "**User:**\n> {prompt}\n\n"
   - Append to current session file using fs.appendFileSync
   - Handle errors silently with console.error logging

2. Update .claude-plugin/plugin.json to register the hook:
   - Add "hooks" section if not present
   - Register "UserPromptSubmit" hook pointing to "hooks/session-recorder.js"

3. Test the implementation:
   - Start Claude Code session
   - Type a user prompt
   - Verify .claude/sessions/session-*.md file is created
   - Verify prompt appears in correct format
   - Test with multiple prompts

4. Mark all checkboxes with [x] when complete
```

## Steel Thread 3: Transcript Parsing for Claude Responses

### Purpose
Read Claude's responses from the transcript file and append them to the session recording.

### Implementation Steps

```text
[x] Write test for transcript file reading
    [x] Test transcript_path is extracted from hook input
    [x] Test transcript file is read successfully
    [x] Test malformed transcript is handled gracefully
    [x] Test missing transcript file doesn't crash

[x] Implement transcript reader
    [x] Extract transcript_path from hook input JSON
    [x] Read transcript file using fs.readFileSync
    [x] Handle file read errors with logging
    [x] Return raw transcript content

[x] Write test for response extraction
    [x] Test latest Claude response is identified
    [x] Test response text is extracted correctly
    [x] Test multi-line responses are preserved
    [x] Test incomplete responses are handled

[x] Implement response parser
    [x] Parse transcript to find Claude's latest response
    [x] Extract response text (may be in JSON or text format)
    [x] Preserve line breaks and formatting
    [x] Handle edge cases (empty responses, partial responses)

[x] Write test for position tracking (Simplified: using Stop hook instead)
    [x] Stop hook fires once per Claude response
    [x] No position tracking needed with Stop hook approach
    [x] Each Stop event processes current transcript
    [x] Session state maintained across hook calls

[x] Implement incremental parsing (Simplified: using Stop hook)
    [x] Stop hook provides transcript at completion
    [x] Extract last assistant message from transcript
    [x] Handle nested content arrays
    [x] Store session path in memory

[x] Write test for response formatting
    [x] Test response formatted as markdown blockquote
    [x] Test blank lines are added for readability
    [x] Test special characters are preserved

[x] Implement response appending
    [x] Format Claude response as "**Claude:**\n> {response}\n\n"
    [x] Handle multi-line responses with proper blockquote formatting
    [x] Append to session file
    [x] Configure Stop hook in plugin.json
```

**Prompt for Coding Agent:**
```text
Implement transcript parsing to capture Claude's responses:

1. Update session-recorder.js to parse Claude Code transcripts:
   - Hook input contains "transcript_path" field with path to transcript file
   - Read the transcript file to extract Claude's latest response
   - Track last read position to avoid re-processing old content
   - Format response as: "**Claude:**\n> {response text}\n\n"
   - Handle multi-line responses by preserving line breaks in blockquote

2. Transcript parsing strategy:
   - Read transcript file (format may be JSON or text)
   - Identify Claude's latest response text
   - Track cursor position to only process new content
   - Handle incomplete responses gracefully

3. Error handling:
   - Missing transcript file -> log and continue
   - Malformed transcript -> log and continue
   - Read errors -> log and continue
   - Never crash Claude Code

4. Test the implementation:
   - Submit a prompt to Claude Code
   - Verify Claude's response appears in session file
   - Verify blockquote formatting is correct
   - Test with long multi-line responses

5. Mark all checkboxes with [x] when complete
```

## Steel Thread 4: PostToolUse Hook for Tool Call Recording

### Purpose
Capture tool calls after execution and append minimal summaries to the session file.

### Implementation Steps

```text
[x] Write test for PostToolUse hook input
    [x] Test hook receives tool_name in JSON input
    [x] Test hook receives tool_input parameters
    [x] Test malformed hook input is handled

[x] Implement tool data extraction
    [x] Parse JSON input from PostToolUse hook
    [x] Extract tool_name from hook data
    [x] Extract tool_input parameters from hook data
    [x] Handle missing or malformed data

[x] Write test for tool call formatters
    [x] Test Read tool: "Read {file_path}"
    [x] Test Write tool: "Write {file_path}"
    [x] Test Edit tool: "Edit {file_path}"
    [x] Test Bash tool: "Bash: {command}"
    [x] Test Grep tool: "Grep '{pattern}'"
    [x] Test Glob tool: "Glob '{pattern}'"
    [x] Test Task tool: "Task {description}"
    [x] Test unknown tools: "ToolName"

[x] Implement tool call formatter
    [x] Create formatToolCall(toolName, toolInput) function
    [x] Use switch/case for different tool types
    [x] Extract relevant parameters for each tool type
    [x] Return formatted string
    [x] Handle unknown tools gracefully

[x] Write test for tool call batching
    [x] Test multiple tool calls are grouped together
    [x] Test tools are listed under "**Tools Used:**" section
    [x] Test blank line added after tool list

[x] Implement tool call aggregation (Simplified: each tool call written immediately)
    [x] Format each tool call with "**Tools Used:**" header
    [x] Append to session file after each tool call
    [x] Session state shared via .current-session file

[x] Configure PostToolUse hook
    [x] Register PostToolUse hook in plugin.json
    [x] Point to session-recorder.js
    [x] Test hook is triggered after tool execution

[x] Write integration test
    [x] Test tool calls appear in session file
    [x] Test formatting matches specification
    [x] Test multiple tools in one response
```

**Prompt for Coding Agent:**
```text
Implement PostToolUse hook to capture tool calls:

1. Update session-recorder.js to handle PostToolUse events:
   - Parse JSON input containing tool_name and tool_input
   - Format tool calls minimally according to these rules:
     - Read: "Read {file_path}"
     - Write: "Write {file_path}"
     - Edit: "Edit {file_path}"
     - Bash: "Bash: {command}"
     - Grep: "Grep '{pattern}'"
     - Glob: "Glob '{pattern}'"
     - Task: "Task {description}"
     - Other tools: Just the tool name

2. Tool call aggregation:
   - Collect multiple tool calls that happen in one response
   - Write them as a bulleted list under "**Tools Used:**"
   - Example format:
     **Tools Used:**
     - Read src/file.ts
     - Bash: npm test
     - Edit package.json

3. Update plugin.json:
   - Register "PostToolUse" hook pointing to hooks/session-recorder.js

4. Test the implementation:
   - Use Claude Code to perform various tool operations
   - Verify tool calls appear in session file
   - Verify formatting is minimal and readable
   - Test with multiple tools in one response

5. Mark all checkboxes with [x] when complete
```

## Steel Thread 5: Session Lifecycle and Hook Coordination

### Purpose
Coordinate all hooks to create a cohesive session recording with proper sequencing and state management.

### Implementation Steps

```text
[ ] Write test for hook coordination
    [ ] Test correct sequence: UserPrompt -> Transcript -> Tools
    [ ] Test state is maintained across hook calls
    [ ] Test session file has correct overall structure

[ ] Implement state management
    [ ] Track current session state (active, waiting for response, etc.)
    [ ] Maintain session file path in memory
    [ ] Track pending tool calls for batching
    [ ] Track last transcript position

[ ] Write test for event sequencing
    [ ] Test user prompt immediately written
    [ ] Test Claude response written after transcript update
    [ ] Test tool calls written before next user prompt
    [ ] Test proper blank line spacing

[ ] Implement event queue (if needed)
    [ ] Ensure events are processed in correct order
    [ ] Handle rapid successive events
    [ ] Prevent race conditions in file writes
    [ ] Flush pending writes appropriately

[ ] Write test for session file format
    [ ] Test complete session matches specification
    [ ] Test all sections are present and formatted correctly
    [ ] Test file is valid markdown
    [ ] Test file is human-readable

[ ] Validate complete session format
    [ ] Review generated session files
    [ ] Ensure header is correct
    [ ] Ensure user/Claude exchanges are properly formatted
    [ ] Ensure tool calls appear in right places
    [ ] Ensure blank lines create readability

[ ] Write test for edge cases
    [ ] Test rapid user inputs
    [ ] Test very long responses
    [ ] Test sessions with no tool calls
    [ ] Test sessions with many tool calls

[ ] Handle edge cases
    [ ] Rate-limit file writes if necessary
    [ ] Handle very large transcript files
    [ ] Handle sessions with thousands of exchanges
    [ ] Optimize for performance
```

**Prompt for Coding Agent:**
```text
Coordinate all hooks for complete session recording:

1. Review and refine session-recorder.js:
   - Ensure proper sequencing: User prompt -> Claude response -> Tools
   - Maintain session state across hook calls
   - Ensure file format matches specification exactly

2. Session file format validation:
   - Header: "# Session: YYYY-MM-DD HH:MM:SS\n\n"
   - User prompts: "**User:**\n> {text}\n\n"
   - Claude responses: "**Claude:**\n> {text}\n\n"
   - Tool calls: "**Tools Used:**\n- Tool summary\n- Tool summary\n\n"

3. State management:
   - Track active session file path
   - Track pending tool calls for batching
   - Track last position in transcript
   - Handle rapid successive events correctly

4. Test complete workflow:
   - Have a full conversation with Claude Code
   - Verify session file has complete, accurate recording
   - Verify markdown formatting is correct
   - Test edge cases (rapid inputs, long responses, many tools)

5. Mark all checkboxes with [x] when complete
```

## Steel Thread 6: Error Handling and Silent Failures

### Purpose
Implement comprehensive error handling to ensure recording failures never interrupt Claude Code sessions.

### Implementation Steps

```text
[ ] Write test for file system errors
    [ ] Test read-only file system
    [ ] Test disk full condition
    [ ] Test permission denied errors
    [ ] Test directory creation failures

[ ] Implement file system error handling
    [ ] Wrap all fs operations in try-catch blocks
    [ ] Log errors to console.error with context
    [ ] Continue execution after errors
    [ ] Never throw unhandled exceptions

[ ] Write test for parsing errors
    [ ] Test malformed JSON input to hooks
    [ ] Test invalid transcript format
    [ ] Test missing required fields
    [ ] Test corrupt session files

[ ] Implement parsing error handling
    [ ] Validate JSON parsing with try-catch
    [ ] Provide default values for missing fields
    [ ] Skip malformed data gracefully
    [ ] Log parsing errors with details

[ ] Write test for concurrent access
    [ ] Test multiple hooks triggered simultaneously
    [ ] Test file lock conflicts
    [ ] Test append operation atomicity

[ ] Handle concurrent access
    [ ] Use synchronous operations for simplicity
    [ ] Handle EAGAIN/EBUSY errors with retry
    [ ] Ensure appends are atomic
    [ ] Log concurrency issues if they occur

[ ] Write test for recovery scenarios
    [ ] Test recovery after failed write
    [ ] Test recovery from missing session file
    [ ] Test recreation of deleted .claude/sessions/ directory

[ ] Implement recovery mechanisms
    [ ] Recreate session file if deleted during session
    [ ] Recreate directory if deleted during session
    [ ] Continue recording after transient failures
    [ ] Track and log recovery events

[ ] Add comprehensive logging
    [ ] Log session start
    [ ] Log each successful write
    [ ] Log all errors with stack traces
    [ ] Use different log levels (debug, error)

[ ] Test error scenarios
    [ ] Manually test disk full condition
    [ ] Test with read-only directory
    [ ] Test with malformed hook inputs
    [ ] Verify Claude Code continues normally in all cases
```

**Prompt for Coding Agent:**
```text
Implement robust error handling for session recording:

1. Error handling requirements:
   - All file system operations must be wrapped in try-catch
   - All JSON parsing must be wrapped in try-catch
   - Errors logged to console.error with context
   - Never throw unhandled exceptions
   - Never crash Claude Code

2. Specific error scenarios to handle:
   - Cannot create .claude/sessions/ directory -> log and skip recording
   - Cannot write to session file -> log and skip this entry
   - Cannot read transcript -> log and skip this response
   - Malformed hook input -> log and skip this event
   - Disk full -> log and skip recording

3. Recovery mechanisms:
   - If session file deleted mid-session, recreate it
   - If directory deleted mid-session, recreate it
   - Continue recording after transient failures

4. Logging strategy:
   - Log to console.error for errors
   - Include context: hook type, file path, error message
   - Include timestamps in log messages
   - Keep logs concise but informative

5. Test error handling:
   - Simulate various error conditions
   - Verify Claude Code continues normally
   - Verify errors are logged appropriately
   - Verify recovery works when possible

6. Mark all checkboxes with [x] when complete
```

## Steel Thread 7: Plugin Integration and Documentation

### Purpose
Complete plugin integration, update documentation, and ensure the feature works seamlessly with the existing plugin.

### Implementation Steps

```text
[ ] Update plugin.json configuration
    [ ] Verify all hooks are registered correctly
    [ ] Test hook paths are correct
    [ ] Ensure JSON is valid
    [ ] Add any necessary metadata

[ ] Write test for plugin installation
    [ ] Test plugin installs correctly
    [ ] Test hooks are activated after installation
    [ ] Test session recording starts automatically
    [ ] Test no user configuration needed

[ ] Test plugin integration
    [ ] Install plugin in fresh environment
    [ ] Start Claude Code session
    [ ] Verify session recording works immediately
    [ ] Test across different workspaces

[ ] Create/update README documentation
    [ ] Document session recording feature
    [ ] Explain where session files are stored
    [ ] Explain file format and structure
    [ ] Add examples of session files

[ ] Write test for feature documentation
    [ ] Test README has accurate information
    [ ] Test examples match actual output
    [ ] Test troubleshooting section is helpful

[ ] Add user-facing documentation
    [ ] Document .claude/sessions/ directory location
    [ ] Explain automatic recording behavior
    [ ] Provide example session file structure
    [ ] Explain how to search/review sessions
    [ ] Add FAQ section

[ ] Write test for Git integration
    [ ] Test .gitignore is not modified
    [ ] Test sessions can be tracked if user wants
    [ ] Test sessions can be ignored if user wants

[ ] Document Git behavior
    [ ] Note that .gitignore is not modified
    [ ] Explain users can choose to track or ignore sessions
    [ ] Provide example .gitignore entry if user wants to ignore

[ ] Create troubleshooting guide
    [ ] Document common issues and solutions
    [ ] Explain how to verify recording is working
    [ ] Explain how to debug issues
    [ ] Provide contact/support information

[ ] Final integration testing
    [ ] Test with various conversation types
    [ ] Test with different tool usage patterns
    [ ] Test session file quality and readability
    [ ] Get feedback on documentation clarity
```

**Prompt for Coding Agent:**
```text
Complete plugin integration and documentation:

1. Plugin configuration:
   - Review .claude-plugin/plugin.json
   - Verify hooks section is correct:
     {
       "hooks": {
         "UserPromptSubmit": "hooks/session-recorder.js",
         "PostToolUse": "hooks/session-recorder.js"
       }
     }
   - Ensure all paths are correct

2. Update README.adoc or create new documentation:
   - Add section about session recording feature
   - Explain automatic recording (always on, no config needed)
   - Document storage location: .claude/sessions/
   - Document filename format: session-YYYY-MM-DD-HHMMSS.md
   - Provide example session file structure
   - Explain that .gitignore is not modified (user choice)

3. Documentation should include:
   - Feature overview
   - Storage location and format
   - Example session file
   - How to review sessions (any text editor, markdown viewer)
   - How to search sessions (grep, text search, etc.)
   - Troubleshooting section
   - FAQ

4. Testing:
   - Install plugin in a test environment
   - Have several conversations with Claude Code
   - Verify session files are created correctly
   - Verify files are readable and well-formatted
   - Test that no user action was required

5. Mark all checkboxes with [x] when complete
```

## Steel Thread 8: Performance Optimization and Polish

### Purpose
Optimize performance, add final polish, and ensure the feature is production-ready.

### Implementation Steps

```text
[ ] Write test for performance metrics
    [ ] Test write latency is minimal
    [ ] Test file size stays reasonable
    [ ] Test memory usage is acceptable
    [ ] Test no noticeable lag in Claude Code

[ ] Profile and optimize
    [ ] Measure file write performance
    [ ] Optimize transcript parsing if slow
    [ ] Consider async writes if synchronous causes issues
    [ ] Minimize memory footprint

[ ] Write test for large sessions
    [ ] Test sessions with 100+ exchanges
    [ ] Test sessions with large responses
    [ ] Test sessions with many tool calls
    [ ] Test file size and performance

[ ] Optimize for large sessions
    [ ] Ensure incremental writes perform well
    [ ] Consider file rotation if sessions get too large
    [ ] Optimize transcript position tracking
    [ ] Test with real-world large sessions

[ ] Write test for code quality
    [ ] Test code passes linting
    [ ] Test code follows Node.js best practices
    [ ] Test code is maintainable
    [ ] Test code is well-documented

[ ] Code quality review
    [ ] Add JSDoc comments to all functions
    [ ] Ensure consistent code style
    [ ] Remove any debug code or console.logs (except errors)
    [ ] Ensure proper error messages
    [ ] Refactor any complex functions

[ ] Write test for edge cases
    [ ] Test with special characters in prompts
    [ ] Test with markdown in prompts/responses
    [ ] Test with very long single-line text
    [ ] Test with emoji and unicode

[ ] Handle edge cases
    [ ] Properly escape markdown if needed
    [ ] Handle unicode correctly in filenames
    [ ] Handle very long lines gracefully
    [ ] Test with various input types

[ ] Final polish
    [ ] Review all error messages for clarity
    [ ] Ensure log messages are helpful
    [ ] Verify session files are aesthetically pleasing
    [ ] Test markdown rendering in various viewers

[ ] Write comprehensive test suite
    [ ] Unit tests for all functions
    [ ] Integration tests for complete flows
    [ ] Error scenario tests
    [ ] Performance tests
```

**Prompt for Coding Agent:**
```text
Optimize and polish the session recording feature:

1. Performance optimization:
   - Profile file write operations
   - Ensure no noticeable lag in Claude Code
   - Optimize transcript parsing for large files
   - Test with large sessions (100+ exchanges)

2. Code quality improvements:
   - Add JSDoc comments to all functions
   - Ensure consistent code style
   - Remove debug code (keep error logging)
   - Refactor complex functions
   - Add code comments where logic is non-obvious

3. Edge case handling:
   - Test with special characters in user prompts
   - Test with markdown content in responses
   - Test with emoji and unicode
   - Test with very long responses

4. Final testing checklist:
   - Test multiple sessions in same workspace
   - Test across different workspaces
   - Test session file markdown renders correctly
   - Test file is human-readable and useful
   - Test with various markdown viewers

5. Production readiness:
   - Ensure all error cases are handled
   - Verify silent failures (no crashes)
   - Confirm no user configuration needed
   - Verify documentation is complete and accurate

6. Mark all checkboxes with [x] when complete
```

## Testing Strategy

### Unit Testing
Each steel thread includes test-first development:
1. Write failing test for new functionality
2. Implement minimal code to pass test
3. Refactor while keeping tests green
4. Move to next test

### Integration Testing
After completing core threads:
1. Test complete conversation recording end-to-end
2. Test all hook types work together
3. Test error recovery paths
4. Test with real Claude Code usage

### Manual Testing Checklist
```
[ ] Fresh installation in new workspace
[ ] Session file created on first prompt
[ ] User prompts recorded correctly
[ ] Claude responses recorded correctly
[ ] Tool calls recorded with correct format
[ ] Multiple exchanges in one session
[ ] Session file is valid markdown
[ ] Session file is human-readable
[ ] Error conditions don't crash Claude Code
[ ] Recording works across multiple sessions
[ ] .claude/sessions/ directory created automatically
```

## Implementation Notes

### Key Design Decisions
1. **Node.js for hooks**: Use Node.js for cross-platform compatibility and ease of JSON parsing
2. **Synchronous writes**: Use synchronous file operations for simplicity and reliability
3. **Silent failures**: All errors logged but never crash Claude Code
4. **Minimal tool summaries**: Only essential info to keep sessions readable
5. **No configuration**: Works automatically with no user setup

### File Format Rationale
- **Markdown**: Universal, human-readable, easy to search
- **Blockquotes**: Clear visual separation of user/Claude text
- **Timestamps in filename**: Easy sorting and identification
- **Minimal metadata**: Focus on conversation content

### Hook Strategy
1. **UserPromptSubmit**: Captures user input immediately
2. **PostToolUse**: Captures tool calls after execution
3. **Transcript reading**: Extracts Claude responses from transcript file
4. **No SessionStart/End hooks**: Create file on first event, no special cleanup

### Code Quality Guidelines
- Use modern JavaScript (ES6+)
- Handle all errors with try-catch
- Log errors with context to console.error
- Use descriptive variable and function names
- Keep functions focused and small
- Add JSDoc comments for public functions
- Test with various inputs

### Performance Considerations
- Append operations are fast and atomic
- Track transcript position to avoid re-parsing
- Batch tool calls to reduce writes
- Flush after each write for crash safety
- Keep session files as plain text for speed

## Success Criteria

✅ Sessions are automatically recorded without user action
✅ All prompts, responses, and tool calls are captured accurately
✅ Session files are readable markdown with correct formatting
✅ Recording never interrupts or slows down Claude Code
✅ Files saved to `.claude/sessions/` with timestamp names
✅ Works reliably even when errors occur during recording
✅ Can review sessions with any text editor or markdown viewer
✅ No configuration required - works out of the box
✅ Silent failures - errors logged but never crash Claude
✅ Session files match specification format exactly

## Change History

(Initially empty - changes will be recorded here as the plan evolves)
