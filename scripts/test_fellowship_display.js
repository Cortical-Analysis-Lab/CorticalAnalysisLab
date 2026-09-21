/* Exercise the actual browser display helpers without a framework or network. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('assets/fellowship-questionnaire.js', 'utf8');
const programs = JSON.parse(fs.readFileSync('data/summer-research/catalog.json', 'utf8')).opportunities;
const context = {URL, Intl, selectedCategories: new Map(), researchAreaLabels: new Map()};
for (const program of programs) for (const category of program.categories) context.researchAreaLabels.set(category.category_slug, category.category_name);
vm.createContext(context);
vm.runInContext(source.match(/  const stateNames = .*;/)[0] + '\n' + source.slice(source.indexOf('  const fieldForYear'), source.indexOf('  const filterIds')) + '\nthis.helpers = {fieldDisplay, stipendDisplay, bundleDetails, card, reportContext, evaluate};', context);
const {fieldDisplay, stipendDisplay, bundleDetails, card, reportContext, evaluate} = context.helpers;
let withReportedStipends = 0;
for (const [index, program] of programs.entries()) {
 const cycle = program.cycles[0];
 const markup = card({opportunity: program}, index);
 const details = bundleDetails(program);
 assert.ok(!markup.includes('undefined') && !details.includes('undefined'), program.public_id);
 assert.ok(markup.includes(`data-result-index="${index}"`));
 assert.ok(!markup.includes('<template'), 'Build detail content only when opened');
 if (program.reported_facts?.stipend?.length && stipendDisplay(cycle) === 'N/A') {
  assert.notEqual(fieldDisplay(program, cycle, 'stipend', stipendDisplay(cycle)), 'N/A');
  assert.ok(details.includes('Reported information') || details.includes('Other reported information'));
  withReportedStipends++;
 }
}
for (const [id, expected] of [['AUTO-53143E217F','$6,000 total'],['AUTO-7555ADC2C0','$600/week'],['AUTO-FDDB8C5E82','$7,000 total']]) {
 const program = programs.find(p => p.public_id === id);
 assert.equal(stipendDisplay(program.cycles[0]), expected);
}
const historical = {bundle_details:[], reported_facts:{stipend:[{reported_cycle:2023,text_years:['2023'],text:'If funded, stipend of $600/week.'}]}};
assert.match(fieldDisplay(historical, {}, 'stipend', 'N/A'), /Reported 2023: If funded, stipend of \$600\/week/);
assert.equal(reportContext(historical.reported_facts.stipend[0]),'Reported 2023');
assert.equal(fieldDisplay(historical, {}, 'stipend', '$7,000 total'),'$7,000 total');
assert.equal(fieldDisplay({}, {}, 'stipend', 'N/A'),'N/A');
const stipend = programs.find(p=>p.public_id === 'AUTO-B574A6CF4C');
assert.match(fieldDisplay(stipend, stipend.cycles[0], 'stipend', stipendDisplay(stipend.cycles[0])), /At least.*deductions/);
const original = programs.find(p=>p.public_id === 'AUTO-7555ADC2C0');
const hostile = {...original,reported_facts:{stipend:[{text:'<script>alert(1)</script> stipend of $600.',source_url:'javascript:alert(1)'}]},cycles:[{...original.cycles[0],stipend_weekly_usd:null,stipend_total_usd:null}]};
const escaped = bundleDetails(hostile);
assert.ok(!escaped.includes('<script>') && !escaped.includes('href="javascript:'));
assert.ok(escaped.includes('&lt;script&gt;'));
const answers = new Map([['year','junior'],['citizenship','us_citizen'],['institutionType','four_year']]);
assert.deepEqual(evaluate(original,answers),evaluate({...original,reported_facts:{eligibility:[{text:'Only students with a GPA of 4.0 may apply.'}]}},answers));
console.log(`Rendered ${programs.length} cards and detail panels; ${withReportedStipends} missing stipend fields expose attributed reports. Display, escaping, cycle context and eligibility-isolation checks passed.`);
