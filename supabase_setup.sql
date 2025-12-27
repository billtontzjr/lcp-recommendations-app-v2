-- ============================================================================
-- LCP RECOMMENDATIONS APP - COMPLETE SUPABASE SETUP
-- Run this entire script in the Supabase SQL Editor
-- ============================================================================

-- 1. CLINICAL RULES TABLE (already exists, but included for completeness)
CREATE TABLE IF NOT EXISTS clinical_rules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(100),
    rule_name VARCHAR(200) NOT NULL,
    condition_description TEXT NOT NULL,
    action_description TEXT NOT NULL,
    applies_to_scenarios TEXT[],
    excludes_scenarios TEXT[],
    adds_scenarios TEXT[],
    priority INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'Dr. Tontz'
);

CREATE INDEX IF NOT EXISTS idx_clinical_rules_category ON clinical_rules(category);
CREATE INDEX IF NOT EXISTS idx_clinical_rules_active ON clinical_rules(is_active);


-- 2. SCENARIOS REFERENCE TABLE
CREATE TABLE IF NOT EXISTS scenarios (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    body_region VARCHAR(50),
    clinical_pattern TEXT,
    key_triggers TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scenarios_body_region ON scenarios(body_region);


-- 3. CASES TABLE (for storing generated LCPs)
CREATE TABLE IF NOT EXISTS cases (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    patient_name VARCHAR(200),
    date_of_birth DATE,
    date_of_injury DATE,
    life_expectancy DECIMAL(5,2),
    total_annual DECIMAL(12,2),
    total_one_time DECIMAL(12,2),
    lifetime_total DECIMAL(12,2),
    grand_total DECIMAL(12,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- 4. CASE ITEMS TABLE
CREATE TABLE IF NOT EXISTS case_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    category VARCHAR(100),
    item VARCHAR(500),
    code_type VARCHAR(20),
    code VARCHAR(50),
    cost DECIMAL(10,2),
    frequency VARCHAR(100),
    annual_cost DECIMAL(10,2),
    one_time_cost DECIMAL(10,2),
    rationale TEXT,
    scenario_code VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_items_case_id ON case_items(case_id);


-- 5. DOCUMENTS TABLE
CREATE TABLE IF NOT EXISTS documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    file_name VARCHAR(500),
    storage_path VARCHAR(1000),
    file_size INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id);


-- 6. AUTO-UPDATE TIMESTAMPS FUNCTION
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';


-- 7. TRIGGERS FOR AUTO-UPDATING TIMESTAMPS
DROP TRIGGER IF EXISTS update_clinical_rules_updated_at ON clinical_rules;
CREATE TRIGGER update_clinical_rules_updated_at
    BEFORE UPDATE ON clinical_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_scenarios_updated_at ON scenarios;
CREATE TRIGGER update_scenarios_updated_at
    BEFORE UPDATE ON scenarios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_cases_updated_at ON cases;
CREATE TRIGGER update_cases_updated_at
    BEFORE UPDATE ON cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- 8. INSERT ALL 61 SCENARIOS
INSERT INTO scenarios (code, name, body_region, description, is_active) VALUES
-- Cervical Spine (C1-C6)
('C1', 'Cervical Herniated Disc, Non-Operative', 'Cervical Spine', 'Structural cervical disc herniation managed non-operatively', true),
('C2', 'Cervical Radiculopathy, No Prior ESI', 'Cervical Spine', 'Active cervical radiculopathy within one year, no prior ESI', true),
('C3', 'Cervical Radiculopathy, Prior Beneficial ESI', 'Cervical Spine', 'Cervical radiculopathy with prior ESI that helped', true),
('C4', 'Cervical Facet Syndrome, Blocks Helped, No Prior RFA', 'Cervical Spine', 'Cervical facet syndrome with beneficial MBB, no prior RFA', true),
('C5', 'Cervical Facet Syndrome, Prior Beneficial RFA', 'Cervical Spine', 'Cervical facet syndrome with prior RFA that helped', true),
('C6', 'Post-Operative Cervical Fusion or Disc Replacement', 'Cervical Spine', 'Patient has undergone ACDF or cervical disc replacement', true),

-- Thoracic Spine (T1-T4)
('T1', 'Thoracic Axial/Facet Pain, Non-Operative', 'Thoracic Spine', 'Thoracic axial pain managed conservatively', true),
('T2', 'Thoracic Radiculopathy, Prior Beneficial ESI', 'Thoracic Spine', 'Thoracic radiculopathy with prior ESI that helped', true),
('T3', 'Thoracic Compression Fracture, Non-Operative', 'Thoracic Spine', 'Thoracic compression fracture managed conservatively', true),
('T4', 'Post-Operative Thoracic Fusion', 'Thoracic Spine', 'Patient has undergone thoracic spinal fusion', true),

-- Lumbar Spine (L1-L7)
('L1', 'Lumbar Disc Herniation, Non-Operative', 'Lumbar Spine', 'Lumbar disc herniation managed non-operatively', true),
('L2', 'Lumbar Radiculopathy, Prior Beneficial ESI', 'Lumbar Spine', 'Lumbar radiculopathy with prior ESI that helped', true),
('L3', 'Lumbar Facet Syndrome, Blocks Helped, No Prior RFA', 'Lumbar Spine', 'Lumbar facet syndrome with beneficial MBB, no prior RFA', true),
('L4', 'Lumbar Facet Syndrome, Prior Beneficial RFA', 'Lumbar Spine', 'Lumbar facet syndrome with prior RFA that helped', true),
('L5', 'Post-Operative Lumbar Discectomy', 'Lumbar Spine', 'Patient has undergone lumbar discectomy', true),
('L6', 'Post-Operative Lumbar Fusion', 'Lumbar Spine', 'Patient has undergone lumbar spinal fusion', true),
('L7', 'Lumbar Radiculopathy, No Prior ESI', 'Lumbar Spine', 'Active lumbar radiculopathy within one year, no prior ESI', true),

-- Shoulder (S1-S6)
('S1', 'Rotator Cuff Tendinopathy or Partial Tear, Non-Operative', 'Shoulder', 'Rotator cuff partial tear managed non-operatively', true),
('S2', 'Full-Thickness Rotator Cuff Tear, Non-Operative', 'Shoulder', 'Full-thickness rotator cuff tear managed non-operatively', true),
('S3', 'Post-Operative Rotator Cuff Repair', 'Shoulder', 'Patient has undergone rotator cuff repair', true),
('S4', 'Shoulder Labral Tear, Non-Operative', 'Shoulder', 'Glenoid labral tear managed non-operatively', true),
('S5', 'Post-Operative Labral Repair', 'Shoulder', 'Patient has undergone labral repair', true),
('S6', 'Shoulder Arthroplasty', 'Shoulder', 'Patient has undergone shoulder replacement', true),

-- Elbow (E1-E6)
('E1', 'Elbow Tendinopathy, Non-Operative', 'Elbow', 'Overuse or traumatic elbow tendinopathy managed conservatively', true),
('E2', 'Post-Operative Elbow Surgery', 'Elbow', 'Elbow surgery (ulnar nerve transposition, tendon repair)', true),
('E3', 'Cubital Tunnel Syndrome, Non-Surgical', 'Elbow', 'Ulnar nerve compression at the elbow managed without surgery', true),
('E4', 'Post-Operative Cubital Tunnel Release', 'Elbow', 'Surgical decompression of the ulnar nerve at the elbow', true),
('E5', 'Elbow Fracture/Dislocation, Non-Operative', 'Elbow', 'Elbow fracture or dislocation managed non-operatively', true),
('E6', 'Post-Operative Elbow Fracture Fixation (ORIF)', 'Elbow', 'Elbow fracture treated with open reduction internal fixation', true),

-- Wrist/Hand (W1-W6)
('W1', 'Wrist/Hand Tendinopathy or Mild Carpal Tunnel, Non-Operative', 'Wrist/Hand', 'Wrist or hand tendinopathy or mild carpal tunnel syndrome managed conservatively', true),
('W2', 'Post-Operative Tendon Repair of the Wrist/Hand', 'Wrist/Hand', 'Surgical repair of wrist/hand tendons', true),
('W3', 'Carpal Tunnel Syndrome, Non-Surgical', 'Wrist/Hand', 'Median nerve compression at the wrist managed without surgery', true),
('W4', 'Post-Operative Carpal Tunnel Release', 'Wrist/Hand', 'Open or endoscopic carpal tunnel release', true),
('W5', 'Wrist Fracture, Non-Operative', 'Wrist/Hand', 'Wrist fracture managed with immobilization', true),
('W6', 'Post-Operative Wrist Fracture Fixation (ORIF)', 'Wrist/Hand', 'Wrist fracture treated with open reduction internal fixation', true),

-- Hip (H1-H6)
('H1', 'Hip Labral Tear, Non-Operative', 'Hip', 'Hip labral tear managed non-operatively', true),
('H2', 'Post-Operative Hip Arthroscopy', 'Hip', 'Patient has undergone hip arthroscopy', true),
('H3', 'Hip Osteoarthritis, Non-Operative', 'Hip', 'Post-traumatic hip osteoarthritis managed non-operatively', true),
('H4', 'Hip Fracture, Non-Operative', 'Hip', 'Hip fracture managed non-operatively', true),
('H5', 'Post-Operative Hip Fracture Fixation (ORIF)', 'Hip', 'Hip fracture treated with open reduction internal fixation', true),
('H6', 'Total Hip Arthroplasty (Primary)', 'Hip', 'Patient has undergone primary total hip arthroplasty', true),

-- Knee (K1-K8)
('K1', 'Meniscus Tear, Non-Operative', 'Knee', 'Meniscal tear managed non-operatively', true),
('K2', 'Post-Operative Knee Arthroscopy', 'Knee', 'Patient has undergone knee arthroscopy', true),
('K3', 'ACL Tear, Non-Operative', 'Knee', 'ACL tear managed non-operatively', true),
('K4', 'Post-Operative ACL Reconstruction', 'Knee', 'Patient has undergone ACL reconstruction', true),
('K5', 'Knee Osteoarthritis, Non-Operative', 'Knee', 'Post-traumatic knee osteoarthritis managed non-operatively', true),
('K6', 'Tibial Plateau Fracture, Non-Operative', 'Knee', 'Tibial plateau fracture managed non-operatively', true),
('K7', 'Post-Operative Tibial Plateau Fracture Fixation (ORIF)', 'Knee', 'Tibial plateau fracture treated with ORIF', true),
('K8', 'Total Knee Arthroplasty (Primary)', 'Knee', 'Patient has undergone primary total knee arthroplasty', true),

-- Foot/Ankle (F1-F12)
('F1', 'Ankle Sprain/Ligament Injury, Non-Operative (Structural)', 'Foot/Ankle', 'Ankle ligament injury with structural damage', true),
('F2', 'Post-Operative Ankle Ligament Reconstruction', 'Foot/Ankle', 'Patient has undergone ankle ligament reconstruction', true),
('F3', 'Achilles Tendon Injury, Non-Operative', 'Foot/Ankle', 'Achilles tendinopathy or tear managed non-operatively', true),
('F4', 'Post-Operative Achilles Tendon Repair', 'Foot/Ankle', 'Patient has undergone Achilles tendon repair', true),
('F5', 'Ankle Fracture, Non-Operative', 'Foot/Ankle', 'Ankle fracture managed non-operatively', true),
('F6', 'Post-Operative Ankle Fracture Fixation (ORIF)', 'Foot/Ankle', 'Ankle fracture treated with ORIF', true),
('F7', 'Ankle Osteoarthritis, Non-Operative', 'Foot/Ankle', 'Post-traumatic ankle osteoarthritis managed non-operatively', true),
('F8', 'Ankle Fusion (Arthrodesis)', 'Foot/Ankle', 'Patient has undergone ankle fusion', true),
('F9', 'Total Ankle Arthroplasty', 'Foot/Ankle', 'Patient has undergone total ankle arthroplasty', true),
('F10', 'Foot Fracture, Non-Operative', 'Foot/Ankle', 'Foot fracture managed non-operatively', true),
('F11', 'Post-Operative Foot Fracture Fixation (ORIF)', 'Foot/Ankle', 'Foot fracture treated with ORIF', true),
('F12', 'Plantar Fasciitis, Non-Operative (Structural)', 'Foot/Ankle', 'Plantar fasciitis with structural fascia damage', true)
ON CONFLICT (code) DO NOTHING;


-- 9. ENABLE ROW LEVEL SECURITY (Optional but recommended)
-- ALTER TABLE clinical_rules ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE case_items ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Create policies for anonymous access (for the app to work)
-- CREATE POLICY "Enable all access for anon" ON clinical_rules FOR ALL USING (true);
-- CREATE POLICY "Enable all access for anon" ON scenarios FOR ALL USING (true);
-- CREATE POLICY "Enable all access for anon" ON cases FOR ALL USING (true);
-- CREATE POLICY "Enable all access for anon" ON case_items FOR ALL USING (true);
-- CREATE POLICY "Enable all access for anon" ON documents FOR ALL USING (true);


-- ============================================================================
-- SETUP COMPLETE!
-- ============================================================================
