# i2code completion — Discussion

## Context (from codebase exploration)

- CLI built with Click 8.3.1, which natively supports shell completion for bash, zsh, and fish
- No completion command or shell integration currently exists
- Users must manually know the `_I2CODE_COMPLETE=<shell>_source i2code` convention
- CLI has 10 subcommand groups, with `plan` alone having 20+ subcommands

## Questions & Answers

### Q1: Scope — built-in Click completion only, or custom completions too?

Click provides automatic completion for command names, option names, and arguments with `type=click.Choice(...)`. This covers most of the i2code CLI already.

However, some arguments are dynamic (e.g., plan file paths, idea directory names) and could benefit from custom completion callbacks.

**Is the scope of this feature:**
A. Expose Click's built-in completion via a friendly command (minimal — just wraps `_I2CODE_COMPLETE`) **← chosen**
B. Expose built-in completion AND add custom completion callbacks for dynamic arguments (e.g., file paths, thread names)

**Answer:** A — just the friendly wrapper. Custom completion callbacks for dynamic arguments can be a separate future idea.

### Q2: Which shells to support?

Click 8.x natively supports completion for:
- bash
- zsh
- fish

The idea file mentions "shells supported by Click," so the default assumption is to support all three. Should we support all three, or focus on a subset?

A. All three (bash, zsh, fish) **← chosen**
B. Just zsh (your current shell based on environment)
C. Other subset

**Answer:** A — support all three shells that Click supports.

### Q3: UX for `i2code completion` (no arguments)

The idea file says `i2code completion` with no arguments should "print brief help." This aligns with how tools like `rustup completions` or `gh completion` work.

**Default assumption:** When called with no arguments, print a short usage message explaining how to install completions, e.g.:

```
Usage: i2code completion <shell>

Generate shell completion scripts.

Supported shells: bash, zsh, fish

To install, add to your shell config:
  eval "$(i2code completion zsh)"
```

Does that match your expectation, or did you have something different in mind?

A. Yes, brief usage with installation instructions (as above) **← chosen**
B. Something different

**Answer:** A — brief usage message with installation instructions for each shell.

### Q4: Command structure — `i2code completion <shell>` or `i2code completion install`?

Some CLI tools (e.g., `gh completion`) just output the script to stdout and let the user pipe it. Others (e.g., `rustup completions`) offer an `install` subcommand that writes to the shell config file automatically.

**Default assumption:** Keep it simple — just output the completion script to stdout. The user pipes or evals it themselves. No auto-install.

A. Output to stdout only (user handles installation) **← chosen**
B. Also provide an `install` subcommand that writes to shell config

**Answer:** A — output to stdout only. Keep it simple.

### Q5: Error handling for unsupported shell argument

If the user runs `i2code completion powershell` (not supported by Click), what should happen?

**Default assumption:** Print an error message listing the supported shells and exit with a non-zero status code. Click's `type=click.Choice(["bash", "zsh", "fish"])` would handle this automatically.

A. Use `click.Choice` to validate the argument (Click handles the error message automatically) **← chosen**
B. Custom error handling

**Answer:** A — use `click.Choice` for automatic validation.

## Classification

**Type: A — User-facing feature**

**Rationale:** This is a CLI usability improvement that directly benefits end users. It makes shell completion discoverable via `i2code completion` rather than requiring users to know Click's internal `_I2CODE_COMPLETE` environment variable convention. It doesn't introduce new architecture, infrastructure, or serve as an educational example.

