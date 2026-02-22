---
name: find-usage
description: Find all production code locations where a class, function, or method is defined and used. Use when the user asks where something is defined, instantiated, invoked, or called in production code.
user-invokable: true
---

# Find Class/Function/Method Usage

Find all production code locations where the specified class, function, or method is defined and used.

## Steps

1. **Definition** — show where it is defined (file, line, containing class/module)
2. **Usage sites** — show where it is used in production code

   For classes, complete ALL of:
   2a. **Instantiation sites** — search for constructor calls
   2b. **Method invocation sites** — read the class to find its public methods,
       then search for call sites of EACH method

   For functions/methods:
   2a. **Call sites** — search for all calls to the function/method

## Output format

Exclude test code. Use a separate table per category:

### Definition
| Location | Class/Function |
|----------|---------------|
| `file.py:line` | `ClassName` |

### Instantiation sites
| Location | Class/Function | Context |
|----------|---------------|---------|
| `file.py:line` | `ClassName()` | `containing_function()` |

### Method invocation sites
| Location | Class/Function | Method |
|----------|---------------|--------|
| `file.py:line` | `ClassName` | `method_name()` |

For top-level functions, put the function name in Class/Function and note "(top-level)" in Context.

## Step 3: Notable usage patterns

After presenting the tables, read the surrounding context of each call site
and identify cross-cutting patterns worth calling out. Examples:

- **Duplicated dispatch logic** — the same if/else or switch appears at every call site,
  suggesting the conditional could be pushed into the called class.
- **Single entry-point construction** — the class is only instantiated in one place
  and passed everywhere else via injection.
- **Unconditional vs conditional calls** — most sites use a conditional but one or two
  call a method unconditionally, hinting at a different semantic role.
- **Unused methods** — a public method with zero production call sites.

Present findings as a short numbered list with file references.
