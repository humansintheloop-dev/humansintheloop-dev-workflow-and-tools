"""Unit tests for Plan.name, Plan.idea_type, Plan.overview properties."""

from i2code.plan_domain.plan import Plan


PREAMBLE_LINES = [
    '# Implementation Plan: Test Project',
    '',
    '## Idea Type',
    '**B. Enhancement** - Improving an existing feature',
    '',
    '---',
    '',
    '## Overview',
    'This plan covers the test project implementation with multiple threads.',
    '',
    '---',
    '',
]


class TestPlanName:

    def test_returns_name_from_heading(self):
        plan = Plan(_preamble_lines=PREAMBLE_LINES)
        assert plan.name == 'Test Project'


class TestPlanIdeaType:

    def test_returns_idea_type_from_section(self):
        plan = Plan(_preamble_lines=PREAMBLE_LINES)
        assert plan.idea_type == '**B. Enhancement** - Improving an existing feature'


class TestPlanOverview:

    def test_returns_overview_from_section(self):
        plan = Plan(_preamble_lines=PREAMBLE_LINES)
        assert plan.overview == 'This plan covers the test project implementation with multiple threads.'
