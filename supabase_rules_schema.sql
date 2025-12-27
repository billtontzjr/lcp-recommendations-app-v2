-- Custom Clinical Rules Schema for LCP Generator
-- These are Dr. Tontz's explicit clinical decision rules that override/supplement the scenario system

-- Drop existing table if recreating
-- DROP TABLE IF EXISTS clinical_rules;

CREATE TABLE IF NOT EXISTS clinical_rules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Rule categorization
    category VARCHAR(50) NOT NULL,  -- 'body_part', 'age', 'treatment_history', 'diagnosis', 'general'
    subcategory VARCHAR(100),        -- e.g., 'cervical', 'lumbar', 'shoulder', etc.

    -- Rule definition
    rule_name VARCHAR(200) NOT NULL,
    condition_description TEXT NOT NULL,  -- Human-readable condition (shown to Claude)
    action_description TEXT NOT NULL,     -- What to do when condition is met

    -- Optional: specific scenario overrides
    applies_to_scenarios TEXT[],          -- e.g., ['C1', 'C4'] or NULL for all
    excludes_scenarios TEXT[],            -- Scenarios this rule excludes
    adds_scenarios TEXT[],                -- Scenarios this rule adds

    -- Rule metadata
    priority INTEGER DEFAULT 100,         -- Higher = applied first (for conflicts)
    is_active BOOLEAN DEFAULT true,

    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'Dr. Tontz'
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_clinical_rules_category ON clinical_rules(category);
CREATE INDEX IF NOT EXISTS idx_clinical_rules_active ON clinical_rules(is_active);

-- Example rules (Dr. Tontz can add/modify these)
INSERT INTO clinical_rules (category, subcategory, rule_name, condition_description, action_description, priority) VALUES

-- Age-based rules
('age', 'elderly',
 'Conservative approach for patients over 75',
 'Patient is 75 years or older',
 'Prefer non-surgical scenarios. Avoid recommending major surgical interventions unless already performed. Focus on pain management and maintenance care.',
 200),

('age', 'elderly',
 'Reduced PT frequency for elderly',
 'Patient is 70 years or older',
 'Physical therapy visits should be limited to 12-18 visits per cycle instead of 24, as elderly patients may have reduced tolerance for intensive therapy.',
 150),

-- Treatment history rules
('treatment_history', 'esi',
 'ESI failure threshold',
 'Patient has had 3 or more ESI series without sustained benefit',
 'Do not recommend additional ESI. Consider surgical consultation or alternative pain management.',
 180),

('treatment_history', 'rfa',
 'RFA effectiveness requirement',
 'Patient has had RFA with less than 50% relief or relief lasting less than 6 months',
 'Do not recommend repeat RFA. The procedure was not effective for this patient.',
 180),

-- Diagnosis-specific rules
('diagnosis', 'myelopathy',
 'Myelopathy requires surgical evaluation',
 'MRI or clinical findings indicate cervical or thoracic myelopathy',
 'Always recommend surgical consultation regardless of other treatment history. Myelopathy is a progressive condition that may require decompression.',
 250),

('diagnosis', 'multilevel',
 'Multilevel disc disease surveillance',
 'Patient has disc herniations or significant pathology at 3 or more spinal levels',
 'Increase imaging surveillance frequency. Consider MRI annually instead of every 2 years for the first 5 years.',
 160),

('diagnosis', 'cauda_equina',
 'Cauda equina is surgical emergency',
 'Any history of cauda equina syndrome symptoms',
 'Always document surgical history or need. This is never managed conservatively long-term.',
 300),

-- Body part specific rules
('body_part', 'cervical',
 'Cervical fusion adjacent segment disease',
 'Patient has had cervical fusion and is more than 10 years post-surgery',
 'Emphasize adjacent segment surveillance. Recommend more frequent imaging of levels above and below fusion.',
 170),

('body_part', 'lumbar',
 'Failed back surgery syndrome',
 'Patient has had 2 or more lumbar surgeries without resolution of symptoms',
 'Focus on pain management rather than additional surgery. Include spinal cord stimulator evaluation if not already tried.',
 190),

-- General rules
('general', 'documentation',
 'Benefit must be documented',
 'Treatment is recommended for continuation',
 'Only recommend continuing a treatment (ESI, RFA, PT, injections) if the medical records explicitly document benefit from prior treatment. "Patient tolerated procedure well" is not sufficient - need documented pain reduction or functional improvement.',
 250),

('general', 'conservative_first',
 'Conservative before invasive',
 'Recommending any interventional procedure',
 'Verify that conservative measures (PT, medications, activity modification) have been tried before recommending injections or surgery. Document the conservative care trial in the rationale.',
 200);

-- Function to update timestamp on modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for auto-updating timestamp
DROP TRIGGER IF EXISTS update_clinical_rules_updated_at ON clinical_rules;
CREATE TRIGGER update_clinical_rules_updated_at
    BEFORE UPDATE ON clinical_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
