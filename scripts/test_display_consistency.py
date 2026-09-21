#!/usr/bin/env python3
"""Regression checks for the internal text/display consistency audit."""
import tempfile
import unittest
from pathlib import Path

from audit_display_consistency import audit, displayed, write_html


def program(**cycle):
    return {'public_id': 'TEST', 'program_name': 'Example',
            'cycles': [cycle], 'bundle_details': []}


class DisplayConsistencyTests(unittest.TestCase):
    def test_zero_stipend_is_not_missing(self):
        opportunity = program(stipend_total_usd=0)
        self.assertEqual(displayed(opportunity, opportunity['cycles'][0], 'stipend'), '0 USD total')

    def test_housing_report_fallback_is_already_displayed(self):
        opportunity = program(housing_status='unknown')
        opportunity['bundle_details'] = [{'housingProvision': 'provided', 'summary': 'Housing is provided.'}]
        findings, _ = audit([opportunity])
        self.assertFalse(any(row['field'] == 'housing' for row in findings))

    def test_historical_amount_is_preserved_without_correction(self):
        opportunity = program(cycle_year=2026)
        opportunity['bundle_details'] = [{'cycle': 2025, 'summary': 'A stipend of $600/week is provided.'}]
        findings, _ = audit([opportunity])
        row = next(row for row in findings if row['field'] == 'stipend')
        self.assertEqual(row['cycle_context'], 'different reported years')
        self.assertEqual(row['displayed_value'], 'N/A')
        self.assertNotIn('stipend_weekly_usd', opportunity['cycles'][0])

    def test_unknown_boilerplate_and_provenance_not_treated_as_evidence(self):
        opportunity = program()
        opportunity['bundle_details'] = [{'benefitNotes': 'No unambiguous housing or meal provision established from the checked pages.',
                                         'catalogFactHistory': [{'summary': '$7000 stipend'}]}]
        findings, coverage = audit([opportunity])
        self.assertEqual(findings, [])
        self.assertEqual(len(coverage), 1)

    def test_possible_conflict_retains_cycle_context(self):
        opportunity = program(cycle_year=2026, duration_weeks=9)
        opportunity['bundle_details'] = [{'cycle': 2025, 'summary': 'A 10-week program.'}]
        findings, _ = audit([opportunity])
        self.assertEqual(findings[0]['finding'], 'possible_value_conflict')
        self.assertEqual(findings[0]['cycle_context'], 'different reported years')

    def test_html_escapes_source_text(self):
        opportunity = program()
        opportunity['bundle_details'] = [{'summary': 'A $7000 stipend <script>alert(1)</script>.'}]
        findings, coverage = audit([opportunity])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.html'
            write_html(path, findings, coverage)
            self.assertNotIn('<script>alert(1)</script>', path.read_text())
            self.assertIn('&lt;script&gt;', path.read_text())

    def test_all_cycles_covered_and_us_city_not_flagged(self):
        opportunity = program(cycle_year=2026)
        opportunity['cycles'].append({'cycle_year': 2025})
        opportunity['institution'] = {'state_code': 'CA'}
        opportunity['bundle_details'] = [{'location': 'Los Angeles, CA', 'summary': 'A $7000 stipend.'}]
        findings, coverage = audit([opportunity])
        self.assertEqual(coverage[0]['cycles_checked'], 2)
        self.assertFalse(any(row['field'] == 'city' for row in findings))
        self.assertEqual({row['primary_display_cycle'] for row in findings}, {True, False})


if __name__ == '__main__':
    unittest.main()
