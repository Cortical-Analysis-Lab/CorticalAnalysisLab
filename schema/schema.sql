PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS institutions (
    institution_id INTEGER PRIMARY KEY,
    institution_slug TEXT NOT NULL UNIQUE,
    institution_name TEXT NOT NULL,
    institution_type TEXT,
    city TEXT,
    state_code TEXT,
    country_code TEXT,
    latitude REAL CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    longitude REAL CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
    website_url TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (institution_name, city, state_code, country_code)
);

CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id INTEGER PRIMARY KEY,
    public_id TEXT NOT NULL UNIQUE,
    institution_id INTEGER NOT NULL REFERENCES institutions(institution_id),
    program_name TEXT NOT NULL,
    network_source TEXT,
    program_type TEXT,
    location_scope TEXT,
    delivery_format TEXT,
    program_url TEXT,
    application_url TEXT,
    notes TEXT,
    active INTEGER CHECK (active IN (0, 1)) DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS program_cycles (
    cycle_id INTEGER PRIMARY KEY,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    cycle_year INTEGER NOT NULL CHECK (cycle_year BETWEEN 2000 AND 2200),
    duration_weeks REAL CHECK (duration_weeks IS NULL OR duration_weeks > 0),
    program_start TEXT,
    program_end TEXT,
    application_open TEXT,
    application_deadline TEXT,
    application_url TEXT,
    deadline_text TEXT,
    status_code TEXT NOT NULL DEFAULT 'unknown' CHECK (status_code IN ('upcoming', 'open', 'closed', 'active', 'unknown')),
    status_text TEXT,
    stipend_total_usd REAL CHECK (stipend_total_usd IS NULL OR stipend_total_usd >= 0),
    stipend_weekly_usd REAL CHECK (stipend_weekly_usd IS NULL OR stipend_weekly_usd >= 0),
    housing_status TEXT NOT NULL DEFAULT 'unknown' CHECK (housing_status IN ('yes', 'no', 'partial', 'allowance', 'assistance', 'local', 'varies', 'unknown')),
    housing_details TEXT,
    meals_status TEXT NOT NULL DEFAULT 'unknown' CHECK (meals_status IN ('yes', 'no', 'partial', 'allowance', 'assistance', 'local', 'varies', 'unknown')),
    meals_details TEXT,
    travel_status TEXT NOT NULL DEFAULT 'unknown' CHECK (travel_status IN ('yes', 'no', 'partial', 'allowance', 'assistance', 'local', 'varies', 'unknown')),
    travel_details TEXT,
    academic_credit_status TEXT NOT NULL DEFAULT 'unknown' CHECK (academic_credit_status IN ('yes', 'no', 'partial', 'allowance', 'assistance', 'local', 'varies', 'unknown')),
    last_verified TEXT,
    data_confidence TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (opportunity_id, cycle_year)
);

CREATE TABLE IF NOT EXISTS eligibility_rules (
    eligibility_rule_id INTEGER PRIMARY KEY,
    cycle_id INTEGER NOT NULL UNIQUE REFERENCES program_cycles(cycle_id) ON DELETE CASCADE,
    external_applicants_status TEXT NOT NULL DEFAULT 'unknown' CHECK (external_applicants_status IN ('yes', 'no', 'limited', 'unknown')),
    citizenship_rule_text TEXT,
    citizenship_us_citizen INTEGER CHECK (citizenship_us_citizen IN (0, 1)),
    citizenship_permanent_resident INTEGER CHECK (citizenship_permanent_resident IN (0, 1)),
    citizenship_international INTEGER CHECK (citizenship_international IN (0, 1)),
    eligible_years_text TEXT,
    first_year_eligible INTEGER CHECK (first_year_eligible IN (0, 1)),
    sophomore_eligible INTEGER CHECK (sophomore_eligible IN (0, 1)),
    junior_eligible INTEGER CHECK (junior_eligible IN (0, 1)),
    senior_eligible INTEGER CHECK (senior_eligible IN (0, 1)),
    graduating_senior_eligible INTEGER CHECK (graduating_senior_eligible IN (0, 1)),
    min_gpa REAL CHECK (min_gpa IS NULL OR min_gpa BETWEEN 0 AND 4.5),
    enrolled_required INTEGER CHECK (enrolled_required IN (0, 1)),
    graduation_rule_text TEXT,
    institution_type_rule_text TEXT,
    two_year_institution_eligible INTEGER CHECK (two_year_institution_eligible IN (0, 1)),
    four_year_institution_eligible INTEGER CHECK (four_year_institution_eligible IN (0, 1)),
    degree_seeking_required INTEGER CHECK (degree_seeking_required IN (0, 1)),
    prior_research_status TEXT NOT NULL DEFAULT 'unknown' CHECK (prior_research_status IN ('required', 'preferred', 'not_required', 'unknown')),
    raw_eligibility_text TEXT,
    other_rule_text TEXT,
    parse_status TEXT NOT NULL DEFAULT 'needs_review' CHECK (parse_status IN ('reviewed', 'needs_review', 'not_applicable'))
);

CREATE TABLE IF NOT EXISTS research_categories (
    category_id INTEGER PRIMARY KEY,
    category_slug TEXT NOT NULL UNIQUE,
    category_name TEXT NOT NULL UNIQUE,
    description TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS research_tags (
    tag_id INTEGER PRIMARY KEY,
    tag_slug TEXT NOT NULL UNIQUE,
    tag_name TEXT NOT NULL UNIQUE,
    tag_group TEXT,
    description TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS research_modes (
    research_mode_id INTEGER PRIMARY KEY,
    mode_code TEXT NOT NULL UNIQUE CHECK (mode_code IN ('wet_lab', 'computational', 'field', 'clinical', 'translational', 'engineering_design', 'theoretical', 'archival', 'qualitative', 'quantitative', 'mixed')),
    mode_name TEXT NOT NULL UNIQUE,
    description TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS opportunity_categories (
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES research_categories(category_id),
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    assignment_method TEXT NOT NULL DEFAULT 'imported',
    PRIMARY KEY (opportunity_id, category_id)
);

CREATE TABLE IF NOT EXISTS opportunity_tags (
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES research_tags(tag_id),
    source_text TEXT,
    assignment_method TEXT NOT NULL DEFAULT 'imported',
    PRIMARY KEY (opportunity_id, tag_id)
);

CREATE TABLE IF NOT EXISTS opportunity_research_modes (
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    research_mode_id INTEGER NOT NULL REFERENCES research_modes(research_mode_id),
    source_text TEXT,
    assignment_method TEXT NOT NULL DEFAULT 'imported',
    PRIMARY KEY (opportunity_id, research_mode_id)
);

CREATE TABLE IF NOT EXISTS sources (
    source_id INTEGER PRIMARY KEY,
    source_url TEXT NOT NULL UNIQUE,
    source_name TEXT,
    source_type TEXT NOT NULL DEFAULT 'official_program',
    publisher TEXT,
    authoritative INTEGER CHECK (authoritative IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS discovery_sources (
    discovery_source_id INTEGER PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN (
        'official_directory', 'aggregator', 'professional_society',
        'government_database', 'grant_database', 'institution_directory',
        'search_engine', 'secondary_lead', 'federal_agency',
        'national_network', 'institutional_universe'
    )),
    source_url TEXT,
    source_priority INTEGER NOT NULL DEFAULT 999,
    discovery_pass INTEGER NOT NULL CHECK (discovery_pass BETWEEN 1 AND 5),
    automated_search_supported INTEGER NOT NULL DEFAULT 0 CHECK (automated_search_supported IN (0, 1)),
    authority_scope TEXT NOT NULL DEFAULT 'discovery_only' CHECK (authority_scope IN ('discovery_only', 'network_rules', 'government_record', 'official_program')),
    notes TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS opportunity_discovery (
    opportunity_discovery_id INTEGER PRIMARY KEY,
    opportunity_id INTEGER REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    candidate_id TEXT,
    discovery_source_id INTEGER NOT NULL REFERENCES discovery_sources(discovery_source_id),
    discovered_at TEXT NOT NULL,
    discovery_url TEXT,
    raw_title TEXT,
    raw_host TEXT,
    discovery_notes TEXT,
    UNIQUE (opportunity_id, candidate_id, discovery_source_id, discovery_url)
);

CREATE TABLE IF NOT EXISTS crawl_targets (
    crawl_target_id INTEGER PRIMARY KEY,
    discovery_source_id INTEGER REFERENCES discovery_sources(discovery_source_id),
    target_name TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK (target_type IN (
        'carnegie_r1', 'carnegie_r2', 'carnegie_rcu', 'ipeds',
        'medical_school', 'nci_cancer_center', 'ctsa_hub',
        'independent_research_institute', 'ffrdc', 'research_hospital',
        'field_station', 'marine_lab', 'museum_observatory_botanical',
        'federal_agency', 'professional_society', 'institutional_domain',
        'network_host', 'other'
    )),
    official_domain TEXT,
    seed_url TEXT,
    priority INTEGER NOT NULL DEFAULT 999,
    search_vocabulary_group TEXT,
    crawl_status TEXT NOT NULL DEFAULT 'not_started' CHECK (crawl_status IN (
        'not_started', 'queued', 'in_progress', 'searched',
        'no_opportunity_found', 'candidates_found', 'inaccessible',
        'deferred', 'error'
    )),
    last_checked TEXT,
    next_check_after TEXT,
    candidates_found INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    UNIQUE (target_type, target_name, official_domain)
);

CREATE TABLE IF NOT EXISTS source_verifications (
    verification_id INTEGER PRIMARY KEY,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    cycle_id INTEGER REFERENCES program_cycles(cycle_id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    date_checked TEXT,
    verification_status TEXT NOT NULL DEFAULT 'unverified' CHECK (verification_status IN ('verified', 'partially_verified', 'conflict', 'stale', 'unverified')),
    fields_supported TEXT,
    conflict_notes TEXT,
    checked_by TEXT,
    evidence_hash TEXT,
    retrieved_at TEXT,
    UNIQUE (opportunity_id, cycle_id, source_id, date_checked)
);

CREATE TABLE IF NOT EXISTS import_runs (
    import_run_id INTEGER PRIMARY KEY,
    source_filename TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_count INTEGER NOT NULL,
    importer_version TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS import_raw_records (
    import_run_id INTEGER NOT NULL REFERENCES import_runs(import_run_id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    public_id TEXT,
    raw_json TEXT NOT NULL,
    PRIMARY KEY (import_run_id, row_number)
);

CREATE INDEX IF NOT EXISTS idx_institutions_map ON institutions(country_code, state_code, city);
CREATE INDEX IF NOT EXISTS idx_opportunities_institution ON opportunities(institution_id);
CREATE INDEX IF NOT EXISTS idx_cycles_year_status ON program_cycles(cycle_year, status_code);
CREATE INDEX IF NOT EXISTS idx_cycles_deadline ON program_cycles(application_deadline);
CREATE INDEX IF NOT EXISTS idx_eligibility_cycle ON eligibility_rules(cycle_id);
CREATE INDEX IF NOT EXISTS idx_opportunity_modes_mode ON opportunity_research_modes(research_mode_id, opportunity_id);
CREATE INDEX IF NOT EXISTS idx_discovery_sources_pass ON discovery_sources(discovery_pass, source_priority);
CREATE INDEX IF NOT EXISTS idx_opportunity_discovery_candidate ON opportunity_discovery(candidate_id);
CREATE INDEX IF NOT EXISTS idx_opportunity_discovery_opportunity ON opportunity_discovery(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_crawl_targets_status ON crawl_targets(target_type, crawl_status, priority);
CREATE INDEX IF NOT EXISTS idx_verifications_opportunity ON source_verifications(opportunity_id, date_checked);

INSERT OR REPLACE INTO schema_metadata(key, value) VALUES ('schema_version', '1.2.0');
