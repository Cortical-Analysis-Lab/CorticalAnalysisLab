"""Index existing narrative statements for display, without inferring facts.

These are attributed reports, never canonical eligibility or numeric filter data.
Keep complete statements, qualifications, source links and their original years.
"""
import re

from audit_display_consistency import NO_EVIDENCE, PATTERNS, snippets

FIELDS = ('stipend', 'duration', 'minimum_gpa', 'housing', 'meals', 'travel',
          'format', 'academic_credit', 'deadline', 'start_end_dates')


def reported_facts(opportunity):
    result = {}
    seen = set()
    for index, report in enumerate(opportunity.get('bundle_details') or []):
        for source_field in ('summary', 'eligibility', 'benefitNotes', 'notes', 'duration'):
            text = report.get(source_field)
            if not isinstance(text, str) or not text.strip():
                continue
            year = (report.get('benefitsCycle') or report.get('cycle')) if source_field == 'benefitNotes' else report.get('cycle')
            years = sorted(set(re.findall(r'\b20\d{2}\b', text)))
            for statement in snippets(text):
                if NO_EVIDENCE.search(statement):
                    continue
                fields = [field for field in FIELDS if re.search(PATTERNS[field], statement, re.I)]
                if source_field == 'eligibility':
                    fields.append('eligibility')
                for field in fields:
                    if field == 'stipend' and not re.search(r'\bstipend\b|\bsalary\b|\bcompensation\b|\breceive\b.{0,25}[$€£]', statement, re.I):
                        continue
                    if field == 'minimum_gpa' and not re.search(r'\b[0-4]\.\d+\b', statement):
                        continue
                    key = (field, statement, year)
                    if key in seen:
                        continue
                    seen.add(key)
                    result.setdefault(field, []).append({
                        'text': statement, 'reported_cycle': year, 'text_years': years,
                        'source_url': report.get('programUrl') or report.get('sourceUrl'),
                        'report_index': index, 'source_field': source_field,
                    })
    for reports in result.values():
        reports.sort(key=lambda item: int(item['reported_cycle']) if str(item['reported_cycle']).isdigit() else 0, reverse=True)
    return result
