/* Exercise the actual browser display helpers without a framework or network. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('assets/fellowship-questionnaire.js', 'utf8');
const programs = JSON.parse(fs.readFileSync('data/summer-research/catalog.json', 'utf8')).opportunities;
const context = {URL, Intl, selectedCategories: new Map(), researchAreaLabels: new Map()};
for (const program of programs) for (const category of program.categories) context.researchAreaLabels.set(category.category_slug, category.category_name);
vm.createContext(context);
vm.runInContext(source.match(/  const stateNames = .*;/)[0] + '\n' + source.slice(source.indexOf('  const fieldForYear'), source.indexOf('  const filterIds')) + '\nthis.helpers = {fieldDisplay, stipendDisplay, bundleDetails, card, reportContext, evaluate, forAudience, locationLabel};', context);
const {fieldDisplay, stipendDisplay, bundleDetails, card, reportContext, evaluate, forAudience, locationLabel} = context.helpers;
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
const answers = new Map([['classYear','junior'],['citizenship','us_citizen'],['institutionType','four_year']]);
assert.deepEqual(evaluate(original,answers),evaluate({...original,reported_facts:{eligibility:[{text:'Only students with a GPA of 4.0 may apply.'}]}},answers));
console.log(`Rendered ${programs.length} cards and detail panels; ${withReportedStipends} missing stipend fields expose attributed reports. Display, escaping, cycle context and eligibility-isolation checks passed.`);

const hsAnswers = new Map([['classYear','high_school'],['citizenship','us_citizen']]);
const hsPrograms = programs.filter(p => p.high_school_details);
assert.equal(hsPrograms.length, 89);
for (const program of hsPrograms) {
 const projected = forAudience(program, 'high_school');
 assert.notEqual(evaluate(projected, hsAnswers).state, 'ineligible', program.public_id);
 assert.equal(projected.cycles[0].last_verified, null, 'Imported review is not independent verification');
 assert.ok(bundleDetails(projected).includes('High-school program information'));
 assert.ok(!card({opportunity:projected}).includes('undefined'));
 if (program.catalog_audience === 'high_school') assert.equal(evaluate(program, answers).state,'ineligible');
 assert.equal(forAudience(program, 'junior'), program, 'College view preserves canonical cycle');
}
assert.equal(evaluate(original,hsAnswers).state, 'ineligible', 'Undergraduate collection does not flood high-school results');
const oneonta = programs.find(p => p.public_id === 'AUTO-C1E6B2C256');
const hsOneonta = forAudience(oneonta, 'high_school');
assert.equal(hsOneonta.cycles[0].housing_status, 'no');
assert.equal(hsOneonta.cycles[0].stipend_total_usd, null);
assert.match(card({opportunity:hsOneonta}), /3,500/);
assert.ok(!card({opportunity:hsOneonta}).includes('$5,000'));
const bu = forAudience(programs.find(p=>p.public_id==='hs:bu-rise'),'high_school');
assert.equal(bu.cycles[0].cycle_year, 2027);
assert.equal(bu.cycles[0].stipend_total_usd, null);
assert.equal(bu.cycles[0].housing_status, 'no', 'Paid housing does not satisfy included-housing filter');
const international = new Map([['classYear','high_school'],['citizenship','international']]);
assert.equal(evaluate(bu,international).state,'ineligible');
assert.notEqual(evaluate(forAudience(programs.find(p=>p.public_id==='hs:ucsb-rmp'),'high_school'),international).state,'ineligible');
const jsep = forAudience(programs.find(p=>p.public_id==='hs:dartmouth-jsep'),'high_school');
assert.equal(locationLabel(jsep),'Greenland, City: N/A');
const hiddenInstitution = {...hsOneonta, cycles:[{...hsOneonta.cycles[0],eligibility:{...hsOneonta.cycles[0].eligibility,four_year_institution_eligible:0}}]};
assert.notEqual(evaluate(hiddenInstitution,new Map([...hsAnswers,['institutionType','four_year']])).state,'ineligible');
// Check school switching/restoration against the actual event handler.
let standing = 'high_school';
const fieldset = {hidden:false,disabled:false};
const grid = {classList:{toggle(name,value){this[name]=value;}}};
const events = {};
const formStub = {querySelector(selector){return selector.includes('classYear') ? (standing ? {value:standing} : null) : grid;},addEventListener(name,handler){events[name]=handler;}};
let queuedReset;
const visibility = {document:{getElementById(){return fieldset;}},form:formStub,setTimeout(fn){queuedReset=fn;}};
vm.createContext(visibility);
vm.runInContext(source.slice(source.indexOf('  const institutionQuestion'),source.indexOf('  form.addEventListener("submit"')),visibility);
assert.ok(fieldset.hidden && fieldset.disabled);
standing='junior'; events.change(); assert.ok(!fieldset.hidden && !fieldset.disabled);
standing='high_school';events.change();events.reset();standing=null;queuedReset();
assert.ok(!fieldset.hidden && !fieldset.disabled, 'Reset restores required college fieldset');
console.log('High-school audience, merged identity, cohort funding, citizenship, locations and questionnaire switching checks passed.');
Object.assign(context,{keyword:'',housing:false,travel:false,open:false,upcoming:false});
vm.runInContext(source.slice(source.indexOf('    const matchesNonLocationFilters'), source.indexOf('    const locationBase')) + '\nthis.preferenceMatches = matchesNonLocationFilters;',context);
const match = program => context.preferenceMatches({opportunity:program,evaluation:{state:'review'}});
context.housing=true;assert.equal(match(bu),false);context.housing=false;
const travelProgram=forAudience(programs.find(p=>p.public_id==='hs:tuskegee-agri-sci-trek'),'high_school');
context.travel=true;assert.equal(match(travelProgram),true);assert.equal(match(bu),false);context.travel=false;
const statusProgram=status=>({...bu,cycles:[{...bu.cycles[0],status_code:status}]});
context.open=true;assert.equal(match(statusProgram('open')),true);assert.equal(match(statusProgram('upcoming')),false);
context.upcoming=true;assert.equal(match(statusProgram('upcoming')),true);assert.equal(match(statusProgram('closed')),false);
context.open=false;assert.equal(match(statusProgram('open')),false);context.upcoming=false;
context.keyword='unlikely-nonexistent-program';assert.equal(match(bu),false);context.keyword='';
context.selectedCategories.set('neuroscience-cognitive','Neuroscience & Cognitive Science');assert.equal(match(bu),true);context.selectedCategories.clear();
console.log('High-school research-area, keyword, included-housing, travel and separate Open/Upcoming preference checks passed.');
