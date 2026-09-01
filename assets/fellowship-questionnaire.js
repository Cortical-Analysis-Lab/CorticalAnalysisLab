document.addEventListener("DOMContentLoaded", async () => {
  const status = document.getElementById("catalog-status");
  const panel = document.getElementById("questionnaire-panel");
  const form = document.getElementById("eligibility-form");
  const resultsPanel = document.getElementById("eligibility-results");
  const resultContainer = document.getElementById("opportunity-results");
  let opportunities = [];

  try {
    const response = await fetch("data/summer-research/catalog.json");
    if (!response.ok) throw new Error(`Catalog request failed (${response.status})`);
    const payload = await response.json();
    opportunities = payload.opportunities || [];
    status.hidden = true;
    panel.hidden = false;
  } catch (error) {
    status.classList.add("error");
    status.textContent = "The fellowship catalog could not be loaded. Please try again later.";
    console.error(error);
    return;
  }

  const fieldForYear = {
    first_year: "first_year_eligible",
    sophomore: "sophomore_eligible",
    junior: "junior_eligible",
    senior: "senior_eligible",
    graduating_senior: "graduating_senior_eligible",
  };

  const answerValue = (data, name) => data.get(name);
  const display = value => value === null || value === undefined || value === "" || value === "unknown" ? "N/A" : value;
  const dateDisplay = value => value ? new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {month: "short", day: "numeric", year: "numeric"}) : "N/A";
  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[character]);

  function evaluate(opportunity, answers) {
    const cycle = opportunity.cycles?.[0];
    const rule = cycle?.eligibility;
    if (!cycle || !rule) return {state: "review", reasons: ["No structured eligibility record is available."]};

    const conflicts = [];
    const unknowns = [];
    const yearField = fieldForYear[answerValue(answers, "classYear")];

    if (rule.external_applicants_status === "no") conflicts.push("External applicants are not accepted.");
    else if (["unknown", "limited"].includes(rule.external_applicants_status)) unknowns.push("External-applicant rules need review.");

    if (rule.min_gpa !== null && Number(answerValue(answers, "gpa")) < Number(rule.min_gpa)) conflicts.push(`Minimum GPA is ${rule.min_gpa.toFixed(2)}.`);
    if (rule.min_gpa === null) unknowns.push("Minimum GPA is N/A.");

    if (yearField && rule[yearField] === 0) conflicts.push("Your class standing is not eligible.");
    else if (yearField && rule[yearField] === null) unknowns.push("Class-standing eligibility needs review.");

    if (rule.enrolled_required === 1 && answerValue(answers, "enrolled") === "no") conflicts.push("Current enrollment is required.");
    else if (rule.enrolled_required === null) unknowns.push("Enrollment requirement is N/A.");

    if (rule.degree_seeking_required === 1 && answerValue(answers, "degreeSeeking") === "no") conflicts.push("Degree-seeking status is required.");
    else if (rule.degree_seeking_required === null) unknowns.push("Degree-seeking requirement is N/A.");

    const institutionField = answerValue(answers, "institutionType") === "two_year" ? "two_year_institution_eligible" : answerValue(answers, "institutionType") === "four_year" ? "four_year_institution_eligible" : null;
    if (institutionField && rule[institutionField] === 0) conflicts.push("Your institution type is not eligible.");
    else if (!institutionField || rule[institutionField] === null) unknowns.push("Institution-type eligibility needs review.");

    const citizenshipField = {us_citizen: "citizenship_us_citizen", permanent_resident: "citizenship_permanent_resident", international: "citizenship_international"}[answerValue(answers, "citizenship")];
    if (citizenshipField && rule[citizenshipField] === 0) conflicts.push("Your citizenship/residency status is not eligible.");
    else if (!citizenshipField || rule[citizenshipField] === null) unknowns.push("Citizenship/residency eligibility needs review.");

    if (answerValue(answers, "enrolledAfter") !== "yes" && rule.graduation_rule_text) unknowns.push("Graduation timing requires review against the official rule.");
    if (rule.parse_status !== "reviewed") unknowns.push("The source eligibility text has not completed structured review.");

    if (conflicts.length) return {state: "ineligible", reasons: conflicts};
    if (unknowns.length) return {state: "review", reasons: [...new Set(unknowns)]};
    return {state: "eligible", reasons: ["No known hard eligibility rules conflict with your answers."]};
  }

  function card({opportunity, evaluation}) {
    const cycle = opportunity.cycles?.[0] || {};
    const institution = opportunity.institution || {};
    const stateLabels = {eligible: "Appears eligible", review: "Needs review", ineligible: "Likely ineligible"};
    return `<article class="eligibility-card">
      <div><h3>${escapeHtml(opportunity.program_name)}</h3><p>${escapeHtml(institution.institution_name)} · ${escapeHtml([institution.city, institution.state_code].filter(Boolean).join(", ") || "N/A")}</p>
      <div class="program-meta"><span class="meta-chip">Deadline: ${escapeHtml(dateDisplay(cycle.application_deadline))}</span><span class="meta-chip">Minimum GPA: ${escapeHtml(display(cycle.eligibility?.min_gpa))}</span><span class="meta-chip">Cycle: ${escapeHtml(display(cycle.cycle_year))}</span></div></div>
      <span class="eligibility-status ${evaluation.state}">${stateLabels[evaluation.state]}</span>
      <ul class="reason-list">${evaluation.reasons.slice(0, 3).map(reason => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>
    </article>`;
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const answers = new FormData(form);
    const evaluated = opportunities.map(opportunity => ({opportunity, evaluation: evaluate(opportunity, answers)}));
    const order = {eligible: 0, review: 1, ineligible: 2};
    evaluated.sort((a, b) => order[a.evaluation.state] - order[b.evaluation.state] || a.opportunity.program_name.localeCompare(b.opportunity.program_name));
    ["eligible", "review", "ineligible"].forEach(stateName => {
      document.getElementById(`${stateName}-count`).textContent = evaluated.filter(item => item.evaluation.state === stateName).length;
    });
    document.getElementById("results-explanation").textContent = "Programs with incomplete official requirements remain in “Need review.” N/A means the catalog does not yet contain a verified value.";
    resultContainer.innerHTML = evaluated.slice(0, 15).map(card).join("") + (evaluated.length > 15 ? `<p class="results-note">Showing the first 15 results. The synchronized map and complete preference-filtered list are the next product phase.</p>` : "");
    panel.hidden = true;
    resultsPanel.hidden = false;
    resultsPanel.scrollIntoView({behavior: "smooth", block: "start"});
  });

  document.getElementById("edit-answers").addEventListener("click", () => {
    resultsPanel.hidden = true;
    panel.hidden = false;
    panel.scrollIntoView({behavior: "smooth", block: "start"});
  });

  document.getElementById("clear-questionnaire").addEventListener("click", () => {
    resultsPanel.hidden = true;
    resultContainer.innerHTML = "";
  });
});
