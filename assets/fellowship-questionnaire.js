document.addEventListener("DOMContentLoaded", async () => {
  const status = document.getElementById("catalog-status");
  const panel = document.getElementById("questionnaire-panel");
  const form = document.getElementById("eligibility-form");
  const resultsPanel = document.getElementById("eligibility-results");
  const resultContainer = document.getElementById("opportunity-results");
  let opportunities = [];
  let evaluatedResults = [];
  const selectedCategories = new Map();
  const selectedLocations = new Map();
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
  const currencyDisplay = value => value === null || value === undefined ? null : new Intl.NumberFormat("en-US", {style: "currency", currency: "USD", maximumFractionDigits: 0}).format(value);
  const stipendDisplay = cycle => {
    const total = currencyDisplay(cycle.stipend_total_usd);
    const weekly = currencyDisplay(cycle.stipend_weekly_usd);
    if (total && weekly) return `${total} total (${weekly}/week)`;
    if (total) return `${total} total`;
    if (weekly) return `${weekly}/week`;
    return "N/A";
  };
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

  function card({opportunity, location: locationVariant}) {
    const cycle = opportunity.cycles?.[0] || {};
    const institution = opportunity.institution || {};
    const location = locationVariant ? `${locationVariant.city}, ${locationVariant.stateCode}` : [institution.city, institution.state_code].filter(Boolean).join(", ") || "N/A";
    const categories = opportunity.categories || [];
    const activeCategories = [...selectedCategories].filter(([slug]) => matchesResearchArea(opportunity, slug));
    const matchesSelectedTag = tag => activeCategories.some(([slug]) => tagMatchesCategory(tag.tag_name, slug));
    const tags = [...(opportunity.tags || [])].sort((a, b) => Number(matchesSelectedTag(b)) - Number(matchesSelectedTag(a))).slice(0, 4);
    const cardCategories = activeCategories.length ? activeCategories.map(([, label]) => label) : categories.map(category => category.category_name);
    return `<article class="eligibility-card">
      <div class="card-status-row"><span class="cycle-status status-badge ${escapeHtml(display(cycle.status_code).toLowerCase())}">${escapeHtml(display(cycle.status_code))}</span></div>
      <h3>${escapeHtml(opportunity.program_name)}</h3><p class="institution-line">${escapeHtml(institution.institution_name)} · ${escapeHtml(location)}</p>
      <dl class="program-details"><div><dt>Deadline</dt><dd>${escapeHtml(dateDisplay(cycle.application_deadline))}</dd></div><div><dt>Format</dt><dd>${escapeHtml(display(opportunity.delivery_format))}</dd></div><div><dt>Duration</dt><dd>${cycle.duration_weeks === null || cycle.duration_weeks === undefined ? "N/A" : `${escapeHtml(cycle.duration_weeks)} weeks`}</dd></div><div><dt>Stipend</dt><dd>${escapeHtml(stipendDisplay(cycle))}</dd></div><div><dt>Housing</dt><dd>${escapeHtml(display(cycle.housing_status))}</dd></div><div><dt>Minimum GPA</dt><dd>${escapeHtml(display(cycle.eligibility?.min_gpa))}</dd></div></dl>
      <div class="program-tags">${cardCategories.map(label => `<span class="meta-chip category-chip">${escapeHtml(label)}</span>`).join("")}${tags.map(tag => `<span class="meta-chip">${escapeHtml(tag.tag_name)}</span>`).join("")}</div>
      <div class="card-actions"><a class="program-link" href="${escapeHtml(opportunity.program_url)}" target="_blank" rel="noopener">View program →</a><span class="verification-date">Verified ${escapeHtml(display(cycle.last_verified))}</span></div>
    </article>`;
  }

  const filterIds = ["filter-keyword", "filter-housing", "filter-travel", "filter-open", "sort-results"];

  function locationVariants(opportunity) {
    const institution = opportunity.institution || {};
    const states = String(institution.state_code || "").split("/").map(value => value.trim());
    const cities = String(institution.city || "").split("/").map(value => value.trim());
    if (states.length > 1 && states.every(state => stateNames[state]) && cities.length === states.length) {
      return states.map((stateCode, index) => ({city: cities[index], stateCode}));
    }
    return [null];
  }

  function expandLocationCards(items) {
    return items.flatMap(item => locationVariants(item.opportunity).map(location => ({...item, location})));
  }

  function populateLocationFilter(items) {
    const locations = [...new Set(items.map(({opportunity, location}) => location?.stateCode || opportunity.institution?.state_code).filter(Boolean))];
    const locationSelect = document.getElementById("filter-state");
    const stateLocations = locations.filter(location => stateNames[location]).sort((a, b) => stateNames[a].localeCompare(stateNames[b]));
    const otherLocations = locations.filter(location => !stateNames[location]).sort((a, b) => a.localeCompare(b));
    locationSelect.replaceChildren(new Option("Add a location…", ""));
    const stateGroup = document.createElement("optgroup");
    stateGroup.label = "States";
    stateLocations.forEach(location => stateGroup.append(new Option(stateNames[location], location)));
    if (stateLocations.length) locationSelect.add(stateGroup);
    if (otherLocations.length) {
      const otherGroup = document.createElement("optgroup");
      otherGroup.label = "Other";
      otherLocations.forEach(location => otherGroup.append(new Option(location, location)));
      locationSelect.add(otherGroup);
    }
    for (const option of locationSelect.options) option.disabled = selectedLocations.has(option.value);
  }

  function renderResults() {
    const keyword = document.getElementById("filter-keyword").value.trim().toLowerCase();
    const housing = document.getElementById("filter-housing").checked;
    const travel = document.getElementById("filter-travel").checked;
    const open = document.getElementById("filter-open").checked;
    const sort = document.getElementById("sort-results").value;

    const matchesNonLocationFilters = ({opportunity, evaluation}) => {
      const cycle = opportunity.cycles?.[0] || {};
      const haystack = [opportunity.program_name, opportunity.institution?.institution_name, opportunity.institution?.city, opportunity.institution?.state_code, ...(opportunity.tags || []).map(tag => tag.tag_name)].join(" ").toLowerCase();
      return evaluation.state !== "ineligible"
        && (!keyword || haystack.includes(keyword))
        && (!selectedCategories.size || [...selectedCategories.keys()].some(category => matchesResearchArea(opportunity, category)))
        && (!housing || cycle.housing_status === "yes")
        && (!travel || ["yes", "allowance"].includes(cycle.travel_status))
        && (!open || ["open", "upcoming"].includes(cycle.status_code));
    };
    const locationBase = expandLocationCards(evaluatedResults.filter(matchesNonLocationFilters));
    populateLocationFilter(locationBase);
    const filtered = locationBase.filter(({opportunity, location}) => !selectedLocations.size || selectedLocations.has(location?.stateCode || opportunity.institution?.state_code));

    filtered.sort((a, b) => {
      const aCycle = a.opportunity.cycles?.[0] || {};
      const bCycle = b.opportunity.cycles?.[0] || {};
      if (sort === "deadline") return (aCycle.application_deadline || "9999").localeCompare(bCycle.application_deadline || "9999");
      if (sort === "stipend") return Number(bCycle.stipend_total_usd || -1) - Number(aCycle.stipend_total_usd || -1);
      if (sort === "location") return (a.location?.stateCode || a.opportunity.institution?.state_code || "ZZ").localeCompare(b.location?.stateCode || b.opportunity.institution?.state_code || "ZZ");
      return a.opportunity.program_name.localeCompare(b.opportunity.program_name);
    });

    const filteredProgramCount = new Set(filtered.map(({opportunity}) => opportunity.opportunity_id)).size;
    document.getElementById("filtered-result-count").textContent = `Showing ${filtered.length} opportunity ${filtered.length === 1 ? "card" : "cards"} from ${filteredProgramCount} ${filteredProgramCount === 1 ? "program" : "programs"}`;
    resultContainer.innerHTML = filtered.length ? filtered.map(card).join("") : `<div class="empty-results">No opportunities match these preference filters. Try clearing one or more filters.</div>`;
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const answers = new FormData(form);
    evaluatedResults = opportunities.map(opportunity => ({opportunity, evaluation: evaluate(opportunity, answers)}));
    const availableCount = evaluatedResults.filter(item => item.evaluation.state !== "ineligible").length;
    document.getElementById("availability-summary").textContent = `${availableCount} eligible opportunities out of ${evaluatedResults.length} total available`;
    document.getElementById("results-explanation").textContent = "N/A means a requirement or program detail has not yet been verified.";
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

  function renderSelections(selectId, listId, selections) {
    const select = document.getElementById(selectId);
    const list = document.getElementById(listId);
    list.replaceChildren();
    for (const [value, label] of selections) {
      const item = document.createElement("li");
      item.className = "selected-preference";
      const text = document.createElement("span");
      text.textContent = label;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `Remove ${label}`);
      remove.addEventListener("click", () => {
        const index = [...list.children].indexOf(item);
        selections.delete(value);
        renderResults();
        renderSelections(selectId, listId, selections);
        (list.children[index]?.querySelector("button") || list.lastElementChild?.querySelector("button") || select).focus();
      });
      item.append(text, remove);
      list.append(item);
    }
    for (const option of select.options) option.disabled = selections.has(option.value);
  }

  const selectionFilters = [
    ["filter-category", "selected-categories", selectedCategories],
    ["filter-state", "selected-locations", selectedLocations],
  ];
  selectionFilters.forEach(([selectId, listId, selections]) => {
    const select = document.getElementById(selectId);
    select.addEventListener("change", () => {
      if (!select.value) return;
      selections.set(select.value, select.selectedOptions[0].textContent);
      select.value = "";
      renderResults();
      renderSelections(selectId, listId, selections);
    });
  });

  filterIds.forEach(id => document.getElementById(id).addEventListener(id === "filter-keyword" ? "input" : "change", renderResults));
  document.getElementById("clear-filters").addEventListener("click", () => {
    selectionFilters.forEach(([selectId, listId, selections]) => {
      selections.clear();
      renderSelections(selectId, listId, selections);
    });
    ["filter-keyword", "filter-category", "filter-state"].forEach(id => { document.getElementById(id).value = ""; });
    ["filter-housing", "filter-travel", "filter-open"].forEach(id => { document.getElementById(id).checked = false; });
    document.getElementById("sort-results").value = "name";
    renderResults();
  });
});
