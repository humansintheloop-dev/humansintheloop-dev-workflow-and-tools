# Click Command Argument Suppression

## Problem

Click injects one function parameter per CLI option. Commands with 5+ options inherently exceed CodeScene's "Excess Number of Function Arguments" threshold of 4. This is a framework constraint, not a design problem — the arguments can't be meaningfully reduced without fighting Click's architecture.

## Solution

Suppress the CodeScene finding on Click command functions with a comment annotation:

```
# @codescene(disable:"Excess Number of Function Arguments")
```

Place the annotation before the decorators, not before the `def` line.

### Reference implementation

- `replace_thread_cmd` in `src/i2code/plan/thread_cli.py` — suppressed because 7 args are inherent to its CLI contract

## When to Apply

- The function is a Click command handler (decorated with `@click.command`)
- The argument count is driven by CLI options, not internal design
- There is no cohesive subset of options that can be grouped into a shared decorator

