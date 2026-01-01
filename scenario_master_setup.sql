-- Scenario Master System Tables for Supabase
-- Run this in the Supabase SQL Editor

-- Table 1: Global Principles/Rules
CREATE TABLE IF NOT EXISTS scenario_global_rules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    rule_number INTEGER NOT NULL,
    rule_text TEXT NOT NULL,
    rule_type VARCHAR(100) DEFAULT 'general',  -- general, sprain_strain, surveillance, etc.
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table 2: Scenario Definitions
CREATE TABLE IF NOT EXISTS scenario_definitions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    scenario_code VARCHAR(10) NOT NULL UNIQUE,  -- C1, C2, L1, S1, etc.
    scenario_name VARCHAR(500) NOT NULL,
    body_region VARCHAR(100) NOT NULL,  -- cervical, thoracic, lumbar, shoulder, elbow, wrist, hip, knee, ankle_foot
    clinical_pattern TEXT NOT NULL,
    key_record_triggers TEXT,
    is_structural BOOLEAN DEFAULT true,  -- Does this require surveillance?
    is_post_operative BOOLEAN DEFAULT false,
    requires_ct_surveillance BOOLEAN DEFAULT false,  -- For fusions
    is_active BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table 3: Scenario Recommendations (items for each scenario)
CREATE TABLE IF NOT EXISTS scenario_recommendations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    scenario_code VARCHAR(10) NOT NULL REFERENCES scenario_definitions(scenario_code),
    item_category VARCHAR(200) NOT NULL,  -- Physicians, Diagnostic Testing, Therapies, etc.
    item_name VARCHAR(500) NOT NULL,
    item_description TEXT,
    frequency VARCHAR(100) NOT NULL,  -- yearly, every_2_years, every_5_years, one_time, etc.
    frequency_display VARCHAR(200),  -- "Annually for life expectancy", "Every 2 years", etc.
    units INTEGER DEFAULT 1,  -- Number of visits/items (e.g., 24 PT visits)
    cpt_code VARCHAR(20),
    fee_type VARCHAR(10) DEFAULT 'PFR',  -- PFR or APC
    is_one_time BOOLEAN DEFAULT false,
    condition_notes TEXT,  -- "Only if prior ESIs helped", etc.
    is_active BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table 4: Scenario Master Document Versions
CREATE TABLE IF NOT EXISTS scenario_master_versions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    document_name VARCHAR(500) NOT NULL,
    version_date DATE NOT NULL,
    raw_content TEXT,  -- Original markdown content
    parsed_at TIMESTAMP WITH TIME ZONE,
    scenario_count INTEGER DEFAULT 0,
    rule_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE scenario_global_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenario_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenario_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenario_master_versions ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all for service key)
CREATE POLICY "Allow all for scenario_global_rules" ON scenario_global_rules FOR ALL USING (true);
CREATE POLICY "Allow all for scenario_definitions" ON scenario_definitions FOR ALL USING (true);
CREATE POLICY "Allow all for scenario_recommendations" ON scenario_recommendations FOR ALL USING (true);
CREATE POLICY "Allow all for scenario_master_versions" ON scenario_master_versions FOR ALL USING (true);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_scenario_code ON scenario_definitions(scenario_code);
CREATE INDEX IF NOT EXISTS idx_scenario_body_region ON scenario_definitions(body_region);
CREATE INDEX IF NOT EXISTS idx_recommendations_scenario ON scenario_recommendations(scenario_code);
