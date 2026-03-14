# Design Pattern Catalog

## Commands

- [Command + Assembler](commands/command-assembler.md) — Implementing and testing Click commands
- [Click Command Argument Suppression](commands/click-argument-suppression.md) — Suppressing CodeScene excess-arguments findings on Click handlers

## Project Structure

- [Package Cohesion](project-structure/package-cohesion.md) — Every package has one responsibility; extract modules that don't fit
- [Test Directory Mirrors Source Package](project-structure/test-mirrors-source.md) — Test files move with their source modules and mirror the package structure

## Refactoring

- [Compose Method](refactoring/compose-method.md) — Extract helpers so a method reads as a narrative at one level of abstraction

## Testing

- [Test Scripts as Simple Wrappers](testing/test-scripts-as-simple-wrappers.md) — Test logic belongs in pytest; shell scripts should only orchestrate

## Dependency Injection

- [Bundle Constructor Parameters](dependency-injection/bundle-constructor-parameters.md) — Reducing constructor args without breaking DI
- [Type DI Fields](dependency-injection/type-di-fields.md) — Typing DI dataclass fields to catch contract violations statically
