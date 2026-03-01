# i2code completion

Add an `i2code completion` command that generates shell completion scripts for bash, zsh, and fish.

## Problem

Click 8.x provides built-in shell completion, but users must know to run `_I2CODE_COMPLETE=zsh_source i2code` to generate the script. This is undiscoverable. A dedicated `completion` command makes it easy to find and use.

## Behavior

- `i2code completion` — prints brief usage help with installation instructions for each shell
- `i2code completion <shell>` — outputs the completion script to stdout (shell is one of: bash, zsh, fish)

## Example usage

```sh
# Generate and install zsh completions
eval "$(i2code completion zsh)"

# Or save to a file
i2code completion bash > ~/.local/share/bash-completion/completions/i2code
```

## Scope

- Wraps Click's built-in completion mechanism only
- No custom completion callbacks for dynamic arguments (future idea)
- No auto-install to shell config files
- Invalid shell argument handled by `click.Choice` validation

## Classification

User-facing feature — CLI usability improvement.
