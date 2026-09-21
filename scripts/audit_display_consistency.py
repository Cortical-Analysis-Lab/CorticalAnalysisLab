#!/usr/bin/env python3
"""Audit local catalog text against displayed fields; never infer corrections.

This is an internal consistency screen, not official-source verification. Output
stays in ignored local review storage, including coverage for every program.
"""
import argparse
import csv
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNKNOWN = (None, '', 'unknown', 'unconfirmed', 'N/A')
PATTERNS = {
    'stipend': r'\bstipend\b|\bsalary\b|\bcompensation\b|\bpaid\b|\breceive\b.{0,25}[$€£]',
    'housing': r'\bhousing\b|\baccommodation\b|\broom and board\b',
    'meals': r'\bmeals?\b|\bfood\b|\bgrocer\w*\b|\broom and board\b',
    'travel': r'\btravel\b|\bairfare\b|\btransportation\b',
    'duration': r'\b(?:\d+(?:\.\d+)?|six|seven|eight|nine|ten|eleven|twelve)[ -]weeks?\b',
    'minimum_gpa': r'\bGPA\b|grade.point average',
    'format': r'\bvirtual\b|\bhybrid\b|\bin.person\b|\bremote\b|\bon.site\b',
    'academic_credit': r'\bacademic credit\b|\bcourse credit\b|\bcollege credit\b',
    'deadline': r'\bdeadline\b|\bapplications?\b.{0,25}\bdue\b',
    'start_end_dates': r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b|\b\d{4}-\d{2}-\d{2}\b',
}
MONEY = re.compile(r'[$€£]|\b(?:USD|CHF|EUR|GBP|dollars)\b', re.I)
NO_EVIDENCE = re.compile(r'no unambiguous|not established|not (?:yet )?(?:confirmed|verified)|need(?:s)? confirmation|no explicit (?:evidence|information)|unknown does not mean', re.I)


def known(value):
    return value not in UNKNOWN


def canonical_displayed(opportunity, cycle, field):
    eligibility = cycle.get('eligibility') or {}
    if field == 'stipend':
        values = [f'{cycle[key]} USD {unit}' for key, unit in
                  [('stipend_total_usd', 'total'), ('stipend_weekly_usd', 'weekly')]
                  if known(cycle.get(key))]
        return '; '.join(values) or 'N/A'
    if field in ('housing', 'meals'):
        value = cycle.get(f'{field}_status')
        if known(value):
            return str(value)
        for report in opportunity.get('bundle_details', []):
            value = report.get(f'{field}Provision')
            if known(value):
                return f'{value} (reported)'
        return 'N/A'
    if field == 'start_end_dates':
        return ' / '.join(str(cycle.get(key) or 'N/A') for key in ('program_start', 'program_end'))
    value = {
        'duration': cycle.get('duration_weeks'),
        'minimum_gpa': eligibility.get('min_gpa'),
        'format': opportunity.get('delivery_format'),
        'academic_credit': cycle.get('academic_credit_status'),
        'deadline': cycle.get('application_deadline'),
        'travel': cycle.get('travel_status'),
        'eligibility': eligibility.get('raw_eligibility_text'),
    }.get(field)
    return str(value) if known(value) else 'N/A'


def displayed(opportunity, cycle, field):
    for report in opportunity.get('bundle_details', []):
        for note in report.get('catalogDisplayNotes', []):
            if note.get('field') == field and note.get('cycle') == cycle.get('cycle_year') and note.get('display'):
                return note['display']
    value = canonical_displayed(opportunity, cycle, field)
    if value == 'N/A' and opportunity.get('reported_facts', {}).get(field):
        return 'Reported information with source/cycle context; canonical value remains unknown'
    return value


def snippets(text):
    # Preserve decimal amounts, ranges, qualifications and truncated source text.
    return [part.strip() for part in re.split(r'\n+|(?<=[.!?])\s+(?=[A-Z])', text) if part.strip()]


def audit(opportunities):
    findings, coverage = [], []
    for opportunity in opportunities:
        before = len(findings)
        cycles = opportunity.get('cycles') or [{}]
        for cycle_index, cycle in enumerate(cycles):
            texts = []
            for index, report in enumerate(opportunity.get('bundle_details', [])):
                for key in ('summary', 'eligibility', 'benefitNotes', 'notes', 'duration'):
                    value = report.get(key)
                    if isinstance(value, str) and value.strip():
                        year = (report.get('benefitsCycle') or report.get('cycle')) if key == 'benefitNotes' else report.get('cycle')
                        texts.append((f'bundle[{index}].{key}', value, year, report.get('programUrl') or report.get('sourceUrl')))
            eligibility = cycle.get('eligibility') or {}
            for key in ('housing_details', 'meals_details', 'travel_details', 'deadline_text', 'status_text'):
                if cycle.get(key):
                    texts.append((key, cycle[key], cycle.get('cycle_year'), opportunity.get('program_url')))
            for key in ('raw_eligibility_text', 'other_rule_text'):
                if eligibility.get(key):
                    texts.append((key, eligibility[key], cycle.get('cycle_year'), opportunity.get('program_url')))

            seen = set()

            def add(field, kind, evidence, source, year, url):
                key = (field, kind, evidence, source)
                if key in seen:
                    return
                seen.add(key)
                canonical_year = cycle.get('cycle_year')
                years_in_text = sorted(set(re.findall(r'\b20\d{2}\b', evidence)))
                relation = 'same reported year' if year and canonical_year and str(year) == str(canonical_year) else 'different reported years' if year and canonical_year else 'year incomplete'
                if years_in_text and year and any(value != str(year) for value in years_in_text):
                    relation += '; text contains other years'
                findings.append({
                    'program_id': opportunity['public_id'], 'program_name': opportunity['program_name'],
                    'field': field, 'finding': kind, 'displayed_value': displayed(opportunity, cycle, field),
                    'canonical_cycle': canonical_year, 'primary_display_cycle': cycle_index == 0,
                    'reported_cycle': year, 'cycle_context': relation, 'years_in_text': ', '.join(years_in_text),
                    'evidence': evidence, 'source_field': source, 'source_url': url or '',
                    'decision': 'Review evidence and cycle before any correction; no value inferred',
                })

            for source, text, year, url in texts:
                if source.endswith('.eligibility') and displayed(opportunity, cycle, 'eligibility') == 'N/A':
                    if not NO_EVIDENCE.search(text):
                        add('eligibility', 'missing_display_field', text, source, year, url)
                for sentence in snippets(text):
                    if NO_EVIDENCE.search(sentence):
                        continue
                    for field, pattern in PATTERNS.items():
                        if not re.search(pattern, sentence, re.I):
                            continue
                        if field == 'minimum_gpa' and not re.search(r'\b[0-4]\.\d+\b', sentence):
                            continue
                        if field == 'start_end_dates' and re.search(PATTERNS['deadline'], sentence, re.I) and not re.search(r'program (?:dates|runs|starts|begins)|from .+ to |through', sentence, re.I):
                            continue
                        current = displayed(opportunity, cycle, field)
                        if current == 'N/A' or (field == 'start_end_dates' and 'N/A' in current):
                            kind = 'missing_display_field'
                            if field == 'stipend' and not MONEY.search(sentence):
                                kind = 'funding_mentioned_without_amount'
                            add(field, kind, sentence, source, year, url)
                        elif field == 'stipend' and MONEY.search(sentence) and canonical_displayed(opportunity, cycle, field) != 'N/A':
                            # Amounts may be other benefits, ranges or historical; do not
                            # equate all dollar figures with a total student stipend.
                            add(field, 'compare_reported_amount', sentence, source, year, url)
                        elif field in ('duration', 'minimum_gpa') and re.fullmatch(r'\d+(?:\.\d+)?', current):
                            number_pattern = r'\b(\d+(?:\.\d+)?)[ -]weeks?\b' if field == 'duration' else r'(?:GPA\s*(?:of|:|>=|at least)?\s*(\d\.\d+)|(\d\.\d+)\s*(?:minimum\s+)?GPA)'
                            matches = re.findall(number_pattern, sentence, re.I)
                            values = [float(value if isinstance(value, str) else next(x for x in value if x)) for value in matches]
                            if values and any(value != float(current) for value in values):
                                add(field, 'possible_value_conflict', sentence, source, year, url)

            for index, report in enumerate(opportunity.get('bundle_details', [])):
                for field in ('housing', 'meals'):
                    value = report.get(f'{field}Provision')
                    canonical = cycle.get(f'{field}_status')
                    other_reports = {r.get(f'{field}Provision') for r in opportunity.get('bundle_details', [])}
                    conflict = (value == 'provided' and canonical == 'no') or (value == 'not_provided' and canonical == 'yes') or {'provided', 'not_provided'} <= other_reports
                    if conflict:
                        add(field, 'possible_value_conflict', f'Reported provision: {value}; canonical: {canonical}', f'bundle[{index}].{field}Provision', report.get('benefitsCycle') or report.get('cycle'), report.get('programUrl'))
                institution = opportunity.get('institution') or {}
                # Audit location completeness without treating an institution address
                # or a bundle region label as an established participant city.
                for field, key, fallback in [('city', 'city', 'location'), ('country', 'country_code', 'country')]:
                    value = report.get(fallback)
                    us_states = set('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())
                    is_us = institution.get('country_code') in ('US', 'USA', 'United States') or (not institution.get('country_code') and institution.get('state_code') in us_states)
                    if is_us:
                        continue  # U.S. cards deliberately show state only.
                    if not institution.get(key) and value:
                        add(field, 'location_evidence_needs_review', str(value), f'bundle[{index}].{fallback}', report.get('cycle'), report.get('programUrl'))
        coverage.append({'program_id': opportunity['public_id'], 'program_name': opportunity['program_name'],
                         'cycles_checked': len(cycles), 'reports_checked': len(opportunity.get('bundle_details', [])),
                         'findings': len(findings) - before})
    return findings, coverage


def write_csv(path, rows):
    if not rows:
        path.write_text('')
        return
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_html(path, findings, coverage):
    """A portable, searchable report; no hosting or third-party assets needed."""
    escape = lambda value: html.escape(str(value if value is not None else 'Undated'))
    cards = []
    for row in findings:
        cards.append(f'''<article data-field="{escape(row['field'])}" data-kind="{escape(row['finding'])}">
<h2>{escape(row['program_name'])}</h2><p class="context">{escape(row['program_id'])} · {escape(row['field'])} · {escape(row['finding'])}</p>
<p><b>Displayed:</b> {escape(row['displayed_value'])}<br><b>Catalog cycle:</b> {escape(row['canonical_cycle'])} · <b>Reported cycle:</b> {escape(row['reported_cycle'])} · {escape(row['cycle_context'])}<br><b>Review:</b> {escape(row.get('review_outcome', 'Unadjudicated candidate'))} — {escape(row['decision'])}</p>
<details><summary>Read evidence and source</summary><blockquote>{escape(row['evidence'])}</blockquote><p>{escape(row['source_field'])}</p><p>{escape(row['source_url'])}</p></details></article>''')
    fields = ''.join(f'<option>{escape(value)}</option>' for value in sorted({r['field'] for r in findings}))
    kinds = ''.join(f'<option>{escape(value)}</option>' for value in sorted({r['finding'] for r in findings}))
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Opportunity consistency audit</title>
<style>body{font:16px/1.5 system-ui;margin:2rem auto;padding:0 1rem;max-width:1000px;color:#242124}h1{font-size:1.8rem}h2{font-size:1.05rem;margin:0}article{border:1px solid #ddd;border-radius:8px;padding:1rem;margin:1rem 0}article[hidden]{display:none}.context{color:#666;font-size:.85rem}blockquote{white-space:pre-wrap;margin:1rem 0;padding-left:1rem;border-left:3px solid #b30838}input,select{font:inherit;padding:.5rem;max-width:100%}label{display:inline-block;margin:.3rem}details{overflow-wrap:anywhere}summary{cursor:pointer;color:#a30838}.filters{position:sticky;top:0;background:white;padding:.5rem 0;border-bottom:1px solid #ddd}</style>
<h1>Opportunity display consistency audit</h1>
<p>Checked COUNT programs and all stored cycles. These are internal review candidates, not confirmed factual errors. Source text may describe another year, track, benefit or only part of a program. No catalog values were changed.</p>
<div class="filters"><label>Search <input id="search" type="search" placeholder="Program, ID or evidence"></label><label>Field <select id="field"><option value="">All</option>FIELDS</select></label><label>Finding <select id="kind"><option value="">All</option>KINDS</select></label><p id="count" aria-live="polite"></p></div><main>CARDS</main>
<script>const cards=[...document.querySelectorAll('article')];const search=document.querySelector('#search'),field=document.querySelector('#field'),kind=document.querySelector('#kind');const text=cards.map(c=>c.textContent.toLowerCase());function filter(){let count=0;cards.forEach((card,i)=>{card.hidden=!!((field.value&&card.dataset.field!==field.value)||(kind.value&&card.dataset.kind!==kind.value)||!text[i].includes(search.value.toLowerCase()));if(!card.hidden)count++;});document.querySelector('#count').textContent=count+' evidence findings shown';}search.addEventListener('input',filter);field.addEventListener('change',filter);kind.addEventListener('change',filter);filter();</script></html>'''
    page = page.replace('COUNT', str(len(coverage))).replace('FIELDS', fields).replace('KINDS', kinds).replace('CARDS', ''.join(cards))
    path.write_text(page)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=ROOT / 'data/summer-research/catalog.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'database/local/review/display-consistency')
    parser.add_argument('--decisions', type=Path, help='Optional local JSON decisions with exact evidence and displayed-value matching')
    args = parser.parse_args()
    raw = args.catalog.read_bytes()
    opportunities = json.loads(raw)['opportunities']
    findings, coverage = audit(opportunities)
    if args.decisions:
        match_fields = ('program_id', 'field', 'finding', 'canonical_cycle', 'reported_cycle', 'displayed_value', 'evidence')
        key = lambda row: tuple(str(row.get(field) if row.get(field) is not None else '') for field in match_fields)
        decisions = {key(row): row for row in json.loads(args.decisions.read_text())}
        for row in findings:
            decision = decisions.get(key(row))
            row['review_outcome'] = decision['review_outcome'] if decision else 'Unadjudicated candidate'
            if decision:
                row['decision'] = decision['decision']
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / 'findings.csv', findings)
    write_csv(args.output / 'coverage.csv', coverage)
    write_html(args.output / 'review.html', findings, coverage)
    counts = Counter(row['field'] for row in findings)
    lines = ['# Catalog display consistency audit', '',
             f'Checked {len(coverage)} programs and {sum(row["cycles_checked"] for row in coverage)} cycle records.',
             f'{sum(bool(row["findings"]) for row in coverage)} programs have candidate discrepancies; {len(findings)} evidence-level findings.', '',
             'This is a local text/field consistency screen, not official-source verification. A finding is a review candidate, not a confirmed error. No canonical values were changed. Missing fields may be appropriate when text is historical, conditional, ambiguous, truncated, or about another benefit/track. No findings does not establish factual accuracy.', '',
             'Checks cover stipend, housing, meals, travel, duration, GPA, format, academic credit, dates/deadlines, eligibility text and missing location components. The audit includes all stored cycles; primary_display_cycle identifies the cycle the UI shows. Archived provenance/history is deliberately excluded.', '',
             '| Field | Programs flagged | Evidence findings |', '|---|---:|---:|']
    for field, count in sorted(counts.items()):
        lines.append(f'| {field} | {len({row["program_id"] for row in findings if row["field"] == field})} | {count} |')
    lines += ['', 'See findings.csv for exact evidence, source URL, displayed value and cycle context; coverage.csv lists every program checked.', '', f'Catalog SHA-256: `{hashlib.sha256(raw).hexdigest()}`', '']
    (args.output / 'REPORT.md').write_text('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
