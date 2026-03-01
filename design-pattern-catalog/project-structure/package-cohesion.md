# Package Cohesion

## Problem

Every package should have a single, cohesive responsibility. Files within a package that don't share that responsibility should be extracted into a sibling or subpackage.

## Example

### Before

`idea_resolver.py` sits at the package root alongside CLI wiring, even though it's a shared domain module:

```
src/i2code/
    cli.py                  # CLI wiring
    idea_resolver.py        # shared domain module — doesn't belong here
```

### After

The domain module is extracted into its own subpackage:

```
src/i2code/
    cli.py                  # CLI wiring — the package's responsibility
src/i2code/idea/
    resolver.py             # shared domain module in its own package
```

## When to Apply

- A package contains files with different responsibilities
- A module is used by multiple sibling packages and you're tempted to place it in a common ancestor
- A package is growing and it's unclear what belongs there

## Key Principles

- **One responsibility per package.** Every package should have a purpose you can state in one sentence.
- **Extract, don't accumulate.** When a new module doesn't fit the package's responsibility, create a sibling or subpackage for it.
- **Shared modules get their own package.** If multiple packages need a module, give it its own package rather than placing it in a common ancestor.
