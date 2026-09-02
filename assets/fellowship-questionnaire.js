document.addEventListener("DOMContentLoaded", async () => {
  const status = document.getElementById("catalog-status");
  const panel = document.getElementById("questionnaire-panel");
  const form = document.getElementById("eligibility-form");
  const resultsPanel = document.getElementById("eligibility-results");
  const resultContainer = document.getElementById("opportunity-results");
  let opportunities = [];
  let evaluatedResults = [];
  const stateLayout = {
    AK:[1,1],AL:[5,8],AR:[4,6],AZ:[4,3],CA:[3,2],CO:[4,4],CT:[3,12],DC:[5,10],DE:[4,10],FL:[7,10],GA:[6,9],HI:[6,2],IA:[2,6],ID:[2,3],IL:[2,7],IN:[2,8],KS:[4,5],KY:[3,7],LA:[5,6],MA:[2,12],MD:[3,10],ME:[1,12],MI:[1,8],MN:[1,6],MO:[3,6],MS:[5,7],MT:[1,4],NC:[4,9],ND:[1,5],NE:[3,5],NH:[1,11],NJ:[3,11],NM:[5,4],NV:[3,3],NY:[2,11],OH:[2,9],OK:[5,5],OR:[2,2],PA:[2,10],RI:[4,12],SC:[5,9],SD:[2,5],TN:[4,7],TX:[6,5],UT:[3,4],VA:[3,9],VT:[1,10],WA:[1,2],WI:[1,7],WV:[3,8],WY:[2,4]
  };
  const stateNames = {AL:"Alabama",AK:"Alaska",AZ:"Arizona",AR:"Arkansas",CA:"California",CO:"Colorado",CT:"Connecticut",DE:"Delaware",DC:"District of Columbia",FL:"Florida",GA:"Georgia",HI:"Hawaii",ID:"Idaho",IL:"Illinois",IN:"Indiana",IA:"Iowa",KS:"Kansas",KY:"Kentucky",LA:"Louisiana",ME:"Maine",MD:"Maryland",MA:"Massachusetts",MI:"Michigan",MN:"Minnesota",MS:"Mississippi",MO:"Missouri",MT:"Montana",NE:"Nebraska",NV:"Nevada",NH:"New Hampshire",NJ:"New Jersey",NM:"New Mexico",NY:"New York",NC:"North Carolina",ND:"North Dakota",OH:"Ohio",OK:"Oklahoma",OR:"Oregon",PA:"Pennsylvania",RI:"Rhode Island",SC:"South Carolina",SD:"South Dakota",TN:"Tennessee",TX:"Texas",UT:"Utah",VT:"Vermont",VA:"Virginia",WA:"Washington",WV:"West Virginia",WI:"Wisconsin",WY:"Wyoming"};

  try {
    const response = await fetch("data/summer-research/catalog.json");
    if (!response.ok) throw new Error(`Catalog request failed (${response.status})`);
    const payload = await response.json();
    opportunities = payload.opportunities || [];
    document.getElementById("summary-programs").textContent = opportunities.length;
    document.getElementById("summary-institutions").textContent = new Set(opportunities.map(opportunity => opportunity.institution?.institution_id).filter(Boolean)).size;
    document.getElementById("summary-topics").textContent = new Set(opportunities.flatMap(opportunity => (opportunity.tags || []).map(tag => tag.tag_id))).size;
    const categories = new Map(opportunities.flatMap(opportunity => opportunity.categories || []).map(category => [category.category_slug, category.category_name]));
    [...categories].sort((a, b) => a[1].localeCompare(b[1])).forEach(([value, label]) => document.getElementById("filter-category").add(new Option(label, value)));
    buildLocationMap();
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
  const categoryTerms = {
    "biomedical-health": ["biomedical", "health", "medicine", "medical", "cancer", "immunology", "public health"],
    "life-sciences": ["biology", "biological", "bioscience", "ecology", "genetics", "genomics", "molecular", "cell biology"],
    "neuroscience-cognitive": ["neuroscience", "neural", "brain", "cognitive"],
    "computer-data-ai": ["computer", "computational", "computing", "data", "machine learning", "artificial intelligence", "ai"],
    "mathematics-statistics": ["mathematics", "math", "statistics", "statistical", "quantitative"],
    "physics-astronomy": ["physics", "astrophysics", "astronomy", "space science"],
    "chemistry-materials": ["chemistry", "chemical", "materials"],
    "engineering": ["engineering", "robotics", "electronics", "devices", "nanotechnology"],
    "earth-environment-ocean": ["earth", "environment", "climate", "ocean", "marine"],
    "social-behavioral": ["psychology", "behavior", "social science", "sociology", "economics", "education"],
    "humanities-arts": ["humanities", "arts", "history", "language", "archaeology"],
  };

  function tagMatchesCategory(tagName, categorySlug) {
    const tag = String(tagName || "").toLowerCase();
    return (categoryTerms[categorySlug] || []).some(term => tag.includes(term));
  }

  function matchesResearchArea(opportunity, categorySlug) {
    if (!categorySlug) return true;
    return (opportunity.categories || []).some(item => item.category_slug === categorySlug)
      || (opportunity.tags || []).some(tag => tagMatchesCategory(tag.tag_name, categorySlug));
  }

  function evaluate(opportunity, answers) {
    const cycle = opportunity.cycles?.[0];
    const rule = cycle?.eligibility;
    if (!cycle || !rule) return {state: "review", reasons: ["No structured eligibility record is available."]};

    const conflicts = [];
    const unknowns = [];
    const yearField = fieldForYear[answerValue(answers, "classYear")];

    if (rule.external_applicants_status === "no") conflicts.push("External applicants are not accepted.");
    else if (["unknown", "limited"].includes(rule.external_applicants_status)) unknowns.push("External-applicant rules need review.");

    const suppliedGpa = answerValue(answers, "gpa").trim();
    if (suppliedGpa && !Number.isFinite(Number(suppliedGpa))) unknowns.push("GPA could not be evaluated.");
    if (suppliedGpa && Number.isFinite(Number(suppliedGpa)) && rule.min_gpa !== null && Number(suppliedGpa) < Number(rule.min_gpa)) conflicts.push(`Minimum GPA is ${rule.min_gpa.toFixed(2)}.`);
    if (!suppliedGpa) unknowns.push("GPA eligibility was not evaluated.");
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

  function card({opportunity}) {
    const cycle = opportunity.cycles?.[0] || {};
    const institution = opportunity.institution || {};
    const location = [institution.city, institution.state_code].filter(Boolean).join(", ") || "N/A";
    const categories = opportunity.categories || [];
    const activeCategory = document.getElementById("filter-category").value;
    const tags = [...(opportunity.tags || [])].sort((a, b) => Number(tagMatchesCategory(b.tag_name, activeCategory)) - Number(tagMatchesCategory(a.tag_name, activeCategory))).slice(0, 4);
    const activeCategoryLabel = activeCategory ? document.getElementById("filter-category").selectedOptions[0]?.textContent : "";
    return `<article class="eligibility-card">
      <div class="card-status-row"><span class="cycle-status status-badge ${escapeHtml(display(cycle.status_code).toLowerCase())}">${escapeHtml(display(cycle.status_code))}</span></div>
      <h3>${escapeHtml(opportunity.program_name)}</h3><p class="institution-line">${escapeHtml(institution.institution_name)} · ${escapeHtml(location)}</p>
      <dl class="program-details"><div><dt>Deadline</dt><dd>${escapeHtml(dateDisplay(cycle.application_deadline))}</dd></div><div><dt>Format</dt><dd>${escapeHtml(display(opportunity.delivery_format))}</dd></div><div><dt>Duration</dt><dd>${cycle.duration_weeks === null || cycle.duration_weeks === undefined ? "N/A" : `${escapeHtml(cycle.duration_weeks)} weeks`}</dd></div><div><dt>Housing</dt><dd>${escapeHtml(display(cycle.housing_status))}</dd></div><div><dt>Minimum GPA</dt><dd>${escapeHtml(display(cycle.eligibility?.min_gpa))}</dd></div></dl>
      <div class="program-tags">${activeCategoryLabel ? `<span class="meta-chip category-chip">${escapeHtml(activeCategoryLabel)}</span>` : categories.map(category => `<span class="meta-chip category-chip">${escapeHtml(category.category_name)}</span>`).join("")}${tags.map(tag => `<span class="meta-chip">${escapeHtml(tag.tag_name)}</span>`).join("")}</div>
      <div class="card-actions"><a class="program-link" href="${escapeHtml(opportunity.program_url)}" target="_blank" rel="noopener">View program →</a><span class="verification-date">Verified ${escapeHtml(display(cycle.last_verified))}</span></div>
    </article>`;
  }

  const filterIds = ["filter-keyword", "filter-category", "filter-state", "filter-housing", "filter-travel", "filter-open", "sort-results"];

  function buildLocationMap() {
    const map = document.getElementById("state-map");
    map.innerHTML = Object.entries(stateLayout).map(([code, [row, column]]) => `<button class="state-tile" type="button" data-location="${code}" style="--row:${row};--column:${column}" aria-label="${stateNames[code]}"><span class="state-code">${code}</span><strong class="state-count" aria-hidden="true"></strong></button>`).join("");
    map.addEventListener("click", event => {
      const button = event.target.closest("button[data-location]");
      if (button && !button.disabled) selectLocation(button.dataset.location);
    });
  }

  function selectLocation(location) {
    document.getElementById("filter-state").value = location;
    renderResults();
  }

  function updateLocationMap(locationBase) {
    const counts = new Map();
    const institutions = new Map();
    locationBase.forEach(({opportunity}) => {
      const institution = opportunity.institution || {};
      const location = institution.state_code;
      const institutionId = institution.institution_id;
      if (!location || !institutionId) return;
      if (!institutions.has(location)) institutions.set(location, new Set());
      institutions.get(location).add(institutionId);
    });
    institutions.forEach((ids, location) => counts.set(location, ids.size));

    const activeLocation = document.getElementById("filter-state").value;
    document.querySelectorAll(".state-tile").forEach(button => {
      const count = counts.get(button.dataset.location) || 0;
      button.classList.toggle("has-opportunities", count > 0);
      button.classList.toggle("is-selected", activeLocation === button.dataset.location);
      button.disabled = count === 0;
      button.querySelector(".state-count").textContent = count || "";
      button.setAttribute("aria-label", `${stateNames[button.dataset.location]}: ${count} matching ${count === 1 ? "institution" : "institutions"}`);
      button.setAttribute("aria-pressed", String(activeLocation === button.dataset.location));
    });

    const otherLocations = [...counts].filter(([location]) => !stateLayout[location]).sort((a, b) => a[0].localeCompare(b[0]));
    document.getElementById("other-location-list").innerHTML = otherLocations.length ? otherLocations.map(([location, count]) => `<button type="button" data-location="${escapeHtml(location)}" class="other-location-button${activeLocation === location ? " is-selected" : ""}" aria-pressed="${activeLocation === location}"><span>${escapeHtml(location)}</span><strong>${count}</strong></button>`).join("") : `<p class="no-other-locations">No other matching locations</p>`;
    document.getElementById("clear-location").hidden = !activeLocation;
  }

  function renderResults() {
    const keyword = document.getElementById("filter-keyword").value.trim().toLowerCase();
    const category = document.getElementById("filter-category").value;
    const state = document.getElementById("filter-state").value;
    const housing = document.getElementById("filter-housing").checked;
    const travel = document.getElementById("filter-travel").checked;
    const open = document.getElementById("filter-open").checked;
    const sort = document.getElementById("sort-results").value;

    const matchesNonLocationFilters = ({opportunity, evaluation}) => {
      const cycle = opportunity.cycles?.[0] || {};
      const haystack = [opportunity.program_name, opportunity.institution?.institution_name, opportunity.institution?.city, opportunity.institution?.state_code, ...(opportunity.tags || []).map(tag => tag.tag_name)].join(" ").toLowerCase();
      return evaluation.state !== "ineligible"
        && (!keyword || haystack.includes(keyword))
        && matchesResearchArea(opportunity, category)
        && (!housing || cycle.housing_status === "yes")
        && (!travel || ["yes", "allowance"].includes(cycle.travel_status))
        && (!open || ["open", "upcoming"].includes(cycle.status_code));
    };
    const locationBase = evaluatedResults.filter(matchesNonLocationFilters);
    updateLocationMap(locationBase);
    const filtered = locationBase.filter(({opportunity}) => !state || opportunity.institution?.state_code === state);

    filtered.sort((a, b) => {
      const aCycle = a.opportunity.cycles?.[0] || {};
      const bCycle = b.opportunity.cycles?.[0] || {};
      if (sort === "deadline") return (aCycle.application_deadline || "9999").localeCompare(bCycle.application_deadline || "9999");
      if (sort === "stipend") return Number(bCycle.stipend_total_usd || -1) - Number(aCycle.stipend_total_usd || -1);
      if (sort === "location") return (a.opportunity.institution?.state_code || "ZZ").localeCompare(b.opportunity.institution?.state_code || "ZZ");
      return a.opportunity.program_name.localeCompare(b.opportunity.program_name);
    });

    document.getElementById("filtered-result-count").textContent = `Showing ${filtered.length} of ${evaluatedResults.length} programs`;
    resultContainer.innerHTML = filtered.length ? filtered.map(card).join("") : `<div class="empty-results">No opportunities match these preference filters. Try clearing one or more filters.</div>`;
    document.getElementById("map-status").textContent = state ? `Opportunity cards filtered to ${stateNames[state] || state}.` : "Opportunity cards show all matching locations.";
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const answers = new FormData(form);
    evaluatedResults = opportunities.map(opportunity => ({opportunity, evaluation: evaluate(opportunity, answers)}));
    const availableCount = evaluatedResults.filter(item => item.evaluation.state !== "ineligible").length;
    document.getElementById("availability-summary").textContent = `${availableCount} eligible opportunities out of ${evaluatedResults.length} total available`;
    document.getElementById("results-explanation").textContent = "Your opportunity list includes programs with no known conflicts. N/A means a requirement or program detail has not yet been verified.";
    renderResults();
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

  filterIds.forEach(id => document.getElementById(id).addEventListener(id === "filter-keyword" ? "input" : "change", renderResults));
  document.getElementById("other-location-list").addEventListener("click", event => {
    const button = event.target.closest("button[data-location]");
    if (button) selectLocation(button.dataset.location);
  });
  document.getElementById("clear-location").addEventListener("click", () => selectLocation(""));
  document.getElementById("clear-filters").addEventListener("click", () => {
    ["filter-keyword", "filter-category", "filter-state"].forEach(id => { document.getElementById(id).value = ""; });
    ["filter-housing", "filter-travel", "filter-open"].forEach(id => { document.getElementById(id).checked = false; });
    document.getElementById("sort-results").value = "name";
    renderResults();
  });
});
