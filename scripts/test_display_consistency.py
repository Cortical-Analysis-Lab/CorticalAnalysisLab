#!/usr/bin/env python3
"""Regression checks for the internal text/display consistency audit."""
import tempfile
import unittest
from pathlib import Path

from audit_display_consistency import audit, displayed, write_html
from reported_catalog_facts import reported_facts


def program(**cycle):
    return {'public_id': 'TEST', 'program_name': 'Example',
            'cycles': [cycle], 'bundle_details': []}


class DisplayConsistencyTests(unittest.TestCase):
    def test_reported_fields_keep_amount_units_qualifications_and_year(self):
        opportunity = program(cycle_year=2026)
        text = 'If funded, the 2024 program offers up to $600/week, including a meal allowance.'
        opportunity['bundle_details'] = [{'cycle': 2025, 'summary': text, 'programUrl': 'https://example.edu/reu'}]
        facts = reported_facts(opportunity)
        # No stipend keyword in this statement: do not misidentify meal support.
        self.assertNotIn('stipend', facts)
        self.assertEqual(facts['meals'][0]['text'], text)
        self.assertEqual(facts['meals'][0]['text_years'], ['2024'])
        self.assertEqual(facts['meals'][0]['reported_cycle'], 2025)
        self.assertNotIn('stipend_weekly_usd', opportunity['cycles'][0])

    def test_reported_stipend_does_not_convert_a_truncated_range(self):
        opportunity = program()
        text = 'A stipend of between $9,000 and…'
        opportunity['bundle_details'] = [{'summary': text}]
        fact = reported_facts(opportunity)['stipend'][0]
        self.assertEqual(fact['text'], text)
        self.assertIsNone(fact['reported_cycle'])

    def test_reported_facts_prefer_dated_reports_without_overwriting_older_text(self):
        opportunity = program()
        opportunity['bundle_details'] = [{'summary': '$5,000 stipend.'}, {'cycle': 2026, 'summary': '$7,000 stipend.'}]
        facts = reported_facts(opportunity)['stipend']
        self.assertEqual([fact['text'] for fact in facts], ['$7,000 stipend.', '$5,000 stipend.'])

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
