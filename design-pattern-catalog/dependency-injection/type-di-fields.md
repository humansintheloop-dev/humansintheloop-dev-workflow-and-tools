# Type DI Fields

## Problem

A dependency injection dataclass holds fields with imprecise types — bare `Callable`, `Any`, or no annotation. The type checker cannot verify that plugged-in implementations satisfy the expected contract. A function returning `None` where `ClaudeResult` is expected passes silently and only fails at runtime.

## Rule

The public members (fields and methods) of a class or dataclass that is injected into another class should be precisely typed. This lets the type checker verify that every implementation satisfies the contract the consumer relies on.

| Element | Description |
|---------|-------------|
| Injected dependency | A class or dataclass passed into another class — its public members define the contract |
| Public members | Fields and methods on the dependency — each should have a precise type annotation |
| Contract type | A Protocol, parameterized `Callable`, concrete type, or ABC used to annotate a public member |
| Consumer | The class that receives the dependency and accesses its public members |

### Reference implementation

- **Injected dependency:** `OrchestratorDeps` in `src/i2code/go_cmd/orchestrator.py`
- **Public members:** `brainstorm_idea_fn`, `create_spec_fn`, `revise_spec_fn`, `create_plan_fn`, `revise_plan_fn` fields
- **Contract type:** `StepFn` Protocol in `src/i2code/go_cmd/orchestrator.py` — `__call__(self, project: IdeaProject) -> ClaudeResult`
- **Consumer:** `Orchestrator` in `src/i2code/go_cmd/orchestrator.py` — accesses step function fields via `self._deps`

## Testing Strategies

### Static type checking catches contract violations

**What is tested:** `OrchestratorDeps` field assignments. Running `pyright` flags any default function whose return type does not match `StepFn`. No runtime test needed — the type checker enforces the contract at the injection boundary.

### Existing unit tests verify runtime behavior

**What is tested:** `Orchestrator._run_step_with_retry` and `_run_python_step` dispatch. Tests in `tests/go-cmd/test_orchestrator_run.py` construct `OrchestratorDeps` with fake step functions and verify the orchestrator calls them and checks `.returncode`.

## When to Apply

- An injected dependency has public members typed as bare `Callable`, `Any`, or untyped

## Key Principles

- **Type public members of the injected dependency.** Precise contract types on public members let the type checker verify every implementation at the assignment boundary.
- **Imprecise types erase contracts.** Bare `Callable`, `Any`, or missing annotations let the type checker accept anything — the consumer's assumptions become unchecked.
- **The injected dependency is high-value typing.** The public member annotations are where the type checker verifies that implementations match what the consumer expects — maximum defect detection for minimum annotation cost.
