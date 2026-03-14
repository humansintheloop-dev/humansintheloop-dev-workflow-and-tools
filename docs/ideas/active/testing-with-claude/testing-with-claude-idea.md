  I believe (please verify) that test_triage_real_claude.py runs real Claude, and it's manually invoked. All other tests mock the subprocess or use FakeClaudeRunner.

  I want similar tests for all of the other callers of ClaudeRunner.run() (which can be non-interactive) or run_batch(), which always is.