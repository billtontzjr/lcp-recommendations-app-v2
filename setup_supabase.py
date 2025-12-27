#!/usr/bin/env python3
"""
Supabase Setup Script for LCP Recommendations App.

This script sets up all necessary tables and populates them with data:
1. Creates clinical_rules table
2. Inserts default clinical rules
3. Creates scenarios table (optional - for reference/admin)
4. Populates scenarios from the master document

Run this script once to initialize your Supabase database.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    exit(1)

from supabase import create_client

print(f"Connecting to Supabase: {SUPABASE_URL}")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================================================================
# STEP 1: Create Tables via SQL (using Supabase's SQL execution)
# =============================================================================

def create_tables():
    """Create necessary tables if they don't exist."""
    print("\n=== Creating Tables ===")

    # We'll use the REST API to check if tables exist and create if needed
    # First, let's try to query the clinical_rules table
    try:
        response = supabase.table('clinical_rules').select('id').limit(1).execute()
        print("✓ clinical_rules table already exists")
        return True
    except Exception as e:
        if 'does not exist' in str(e) or '42P01' in str(e):
            print("clinical_rules table does not exist - needs to be created via SQL Editor")
            print("\nPlease run the following SQL in your Supabase SQL Editor:")
            print("-" * 60)
            print(get_create_tables_sql())
            print("-" * 60)
            return False
        else:
            # Table might exist but have other issues
            print(f"Note: {e}")
            return True


def get_create_tables_sql():
    """Return SQL to create all necessary tables."""
    return """
-- Clinical Rules Table
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

-- Scenarios Reference Table (optional - for admin/reference)
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

-- Cases table (for storing generated LCPs)
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

-- Case Items table
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

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    file_name VARCHAR(500),
    storage_path VARCHAR(1000),
    file_size INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id);

-- Function to auto-update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating timestamps
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
"""


# =============================================================================
# STEP 2: Insert Default Clinical Rules
# =============================================================================

DEFAULT_RULES = [
    {
        "category": "general",
        "rule_name": "Structural injuries only",
        "condition_description": "Any body region being evaluated",
        "action_description": "Only include scenarios for STRUCTURAL injuries (herniations, tears, fractures, stenosis). Sprains and strains heal in 6-12 weeks and do NOT require long-term care or surveillance.",
        "priority": 300
    },
    {
        "category": "general",
        "rule_name": "Benefit must be documented",
        "condition_description": "Treatment is recommended for continuation",
        "action_description": "Only recommend continuing a treatment (ESI, RFA, PT, injections) if the medical records explicitly document benefit from prior treatment. 'Patient tolerated procedure well' is not sufficient - need documented pain reduction or functional improvement.",
        "priority": 250
    },
    {
        "category": "general",
        "rule_name": "Conservative before invasive",
        "condition_description": "Recommending any interventional procedure",
        "action_description": "Verify that conservative measures (PT, medications, activity modification) have been tried before recommending injections or surgery.",
        "priority": 200
    },
    {
        "category": "general",
        "rule_name": "Structural injury surveillance rule",
        "condition_description": "Any structural injury to a body part is identified",
        "action_description": "Any structural injury requires surveillance at minimum: radiographs and MRIs every other year for life expectancy. Spine fusions additionally require CT scan every 5 years.",
        "priority": 280
    },
    {
        "category": "treatment_history",
        "rule_name": "ESI failure threshold",
        "condition_description": "Patient has had 3 or more ESI series without sustained benefit",
        "action_description": "Do not recommend additional ESI. Consider surgical consultation or alternative pain management.",
        "priority": 180
    },
    {
        "category": "treatment_history",
        "rule_name": "RFA requires documented benefit",
        "condition_description": "Considering RFA recommendation",
        "action_description": "Only recommend RFA if medial branch blocks provided documented significant relief (typically 80%+ for diagnostic blocks). If prior RFA provided less than 50% relief or lasted less than 6 months, do not recommend repeat RFA.",
        "priority": 180
    },
    {
        "category": "treatment_history",
        "rule_name": "One-time vs Annual RFA",
        "condition_description": "Patient has beneficial medial branch or facet blocks",
        "action_description": "If NO prior RFA, recommend only ONE-TIME RFA. If there HAS been prior RFA with documented benefit, then recommend ANNUAL RFA for life expectancy.",
        "priority": 190
    },
    {
        "category": "treatment_history",
        "rule_name": "One-time vs Annual ESI",
        "condition_description": "Patient has radiculopathy within one year of LCP",
        "action_description": "If NO prior ESI, recommend ONE-TIME ESI. If there HAS been prior ESI with documented benefit, recommend ANNUAL ESI (up to 3 per year) for life expectancy.",
        "priority": 190
    },
    {
        "category": "diagnosis",
        "rule_name": "Myelopathy is serious",
        "condition_description": "MRI or clinical findings indicate myelopathy",
        "action_description": "Myelopathy requires surgical evaluation. This is a progressive condition - always recommend surgical consultation if present.",
        "priority": 250
    },
    {
        "category": "diagnosis",
        "rule_name": "Cauda equina is surgical emergency",
        "condition_description": "Any history of cauda equina syndrome symptoms",
        "action_description": "Always document surgical history or need. This is never managed conservatively long-term.",
        "priority": 300
    },
    {
        "category": "diagnosis",
        "rule_name": "Multilevel disc disease surveillance",
        "condition_description": "Patient has disc herniations or significant pathology at 3 or more spinal levels",
        "action_description": "Increase imaging surveillance frequency. Consider MRI annually instead of every 2 years for the first 5 years.",
        "priority": 160
    },
    {
        "category": "age",
        "rule_name": "Elderly patient considerations",
        "condition_description": "Patient is 75 years or older",
        "action_description": "Be more conservative with elderly patients. Prefer non-surgical management unless surgery has already been performed. Consider reduced PT visit frequencies.",
        "priority": 150
    },
    {
        "category": "age",
        "rule_name": "Reduced PT for elderly",
        "condition_description": "Patient is 70 years or older",
        "action_description": "Physical therapy visits should be limited to 12-18 visits per cycle instead of 24, as elderly patients may have reduced tolerance for intensive therapy.",
        "priority": 140
    },
    {
        "category": "body_part",
        "subcategory": "cervical",
        "rule_name": "Adjacent segment disease surveillance",
        "condition_description": "Patient has had cervical fusion and is more than 10 years post-surgery",
        "action_description": "Emphasize adjacent segment surveillance. Recommend more frequent imaging of levels above and below fusion. Adjacent segment fusion anticipated at 17 years post-index surgery.",
        "priority": 170
    },
    {
        "category": "body_part",
        "subcategory": "lumbar",
        "rule_name": "Failed back surgery syndrome",
        "condition_description": "Patient has had 2 or more lumbar surgeries without resolution of symptoms",
        "action_description": "Focus on pain management rather than additional surgery. Include spinal cord stimulator evaluation if not already tried.",
        "priority": 190
    },
]


def insert_default_rules():
    """Insert default clinical rules if they don't exist."""
    print("\n=== Inserting Default Clinical Rules ===")

    try:
        # Check if rules already exist
        response = supabase.table('clinical_rules').select('id').execute()
        existing_count = len(response.data) if response.data else 0

        if existing_count > 0:
            print(f"✓ {existing_count} rules already exist in database")
            return True

        # Insert rules
        for rule in DEFAULT_RULES:
            rule['is_active'] = True
            rule['created_by'] = 'Dr. Tontz'

        response = supabase.table('clinical_rules').insert(DEFAULT_RULES).execute()

        if response.data:
            print(f"✓ Inserted {len(response.data)} clinical rules")
            return True
        else:
            print("✗ Failed to insert rules")
            return False

    except Exception as e:
        print(f"✗ Error inserting rules: {e}")
        return False


# =============================================================================
# STEP 3: Insert Scenarios Reference Data
# =============================================================================

SCENARIOS_DATA = [
    # Cervical Spine
    {"code": "C1", "name": "Cervical Herniated Disc, Non-Operative", "body_region": "Cervical Spine", "description": "Structural cervical disc herniation managed non-operatively"},
    {"code": "C2", "name": "Cervical Radiculopathy, No Prior ESI", "body_region": "Cervical Spine", "description": "Active cervical radiculopathy within one year, no prior ESI"},
    {"code": "C3", "name": "Cervical Radiculopathy, Prior Beneficial ESI", "body_region": "Cervical Spine", "description": "Cervical radiculopathy with prior ESI that helped"},
    {"code": "C4", "name": "Cervical Facet Syndrome, Blocks Helped, No Prior RFA", "body_region": "Cervical Spine", "description": "Cervical facet syndrome with beneficial MBB, no prior RFA"},
    {"code": "C5", "name": "Cervical Facet Syndrome, Prior Beneficial RFA", "body_region": "Cervical Spine", "description": "Cervical facet syndrome with prior RFA that helped"},
    {"code": "C6", "name": "Post-Operative Cervical Fusion or Disc Replacement", "body_region": "Cervical Spine", "description": "Patient has undergone ACDF or cervical disc replacement"},

    # Thoracic Spine
    {"code": "T1", "name": "Thoracic Axial/Facet Pain, Non-Operative", "body_region": "Thoracic Spine", "description": "Thoracic axial pain managed conservatively"},
    {"code": "T2", "name": "Thoracic Radiculopathy, Prior Beneficial ESI", "body_region": "Thoracic Spine", "description": "Thoracic radiculopathy with prior ESI that helped"},
    {"code": "T3", "name": "Thoracic Compression Fracture, Non-Operative", "body_region": "Thoracic Spine", "description": "Thoracic compression fracture managed conservatively"},
    {"code": "T4", "name": "Post-Operative Thoracic Fusion", "body_region": "Thoracic Spine", "description": "Patient has undergone thoracic spinal fusion"},

    # Lumbar Spine
    {"code": "L1", "name": "Lumbar Disc Herniation, Non-Operative", "body_region": "Lumbar Spine", "description": "Lumbar disc herniation managed non-operatively"},
    {"code": "L2", "name": "Lumbar Radiculopathy, Prior Beneficial ESI", "body_region": "Lumbar Spine", "description": "Lumbar radiculopathy with prior ESI that helped"},
    {"code": "L3", "name": "Lumbar Facet Syndrome, Blocks Helped, No Prior RFA", "body_region": "Lumbar Spine", "description": "Lumbar facet syndrome with beneficial MBB, no prior RFA"},
    {"code": "L4", "name": "Lumbar Facet Syndrome, Prior Beneficial RFA", "body_region": "Lumbar Spine", "description": "Lumbar facet syndrome with prior RFA that helped"},
    {"code": "L5", "name": "Post-Operative Lumbar Discectomy", "body_region": "Lumbar Spine", "description": "Patient has undergone lumbar discectomy"},
    {"code": "L6", "name": "Post-Operative Lumbar Fusion", "body_region": "Lumbar Spine", "description": "Patient has undergone lumbar spinal fusion"},
    {"code": "L7", "name": "Lumbar Radiculopathy, No Prior ESI", "body_region": "Lumbar Spine", "description": "Active lumbar radiculopathy within one year, no prior ESI"},

    # Shoulder
    {"code": "S1", "name": "Rotator Cuff Tendinopathy or Partial Tear, Non-Operative", "body_region": "Shoulder", "description": "Rotator cuff partial tear managed non-operatively"},
    {"code": "S2", "name": "Full-Thickness Rotator Cuff Tear, Non-Operative", "body_region": "Shoulder", "description": "Full-thickness rotator cuff tear managed non-operatively"},
    {"code": "S3", "name": "Post-Operative Rotator Cuff Repair", "body_region": "Shoulder", "description": "Patient has undergone rotator cuff repair"},
    {"code": "S4", "name": "Shoulder Labral Tear, Non-Operative", "body_region": "Shoulder", "description": "Glenoid labral tear managed non-operatively"},
    {"code": "S5", "name": "Post-Operative Labral Repair", "body_region": "Shoulder", "description": "Patient has undergone labral repair"},
    {"code": "S6", "name": "Shoulder Arthroplasty", "body_region": "Shoulder", "description": "Patient has undergone shoulder replacement"},

    # Elbow
    {"code": "E1", "name": "Elbow Tendinopathy, Non-Operative", "body_region": "Elbow", "description": "Overuse or traumatic elbow tendinopathy managed conservatively"},
    {"code": "E2", "name": "Post-Operative Elbow Surgery", "body_region": "Elbow", "description": "Elbow surgery (ulnar nerve transposition, tendon repair)"},
    {"code": "E3", "name": "Cubital Tunnel Syndrome, Non-Surgical", "body_region": "Elbow", "description": "Ulnar nerve compression at the elbow managed without surgery"},
    {"code": "E4", "name": "Post-Operative Cubital Tunnel Release", "body_region": "Elbow", "description": "Surgical decompression of the ulnar nerve at the elbow"},
    {"code": "E5", "name": "Elbow Fracture/Dislocation, Non-Operative", "body_region": "Elbow", "description": "Elbow fracture or dislocation managed non-operatively"},
    {"code": "E6", "name": "Post-Operative Elbow Fracture Fixation (ORIF)", "body_region": "Elbow", "description": "Elbow fracture treated with open reduction internal fixation"},

    # Wrist/Hand
    {"code": "W1", "name": "Wrist/Hand Tendinopathy or Mild Carpal Tunnel, Non-Operative", "body_region": "Wrist/Hand", "description": "Wrist or hand tendinopathy or mild carpal tunnel syndrome managed conservatively"},
    {"code": "W2", "name": "Post-Operative Tendon Repair of the Wrist/Hand", "body_region": "Wrist/Hand", "description": "Surgical repair of wrist/hand tendons"},
    {"code": "W3", "name": "Carpal Tunnel Syndrome, Non-Surgical", "body_region": "Wrist/Hand", "description": "Median nerve compression at the wrist managed without surgery"},
    {"code": "W4", "name": "Post-Operative Carpal Tunnel Release", "body_region": "Wrist/Hand", "description": "Open or endoscopic carpal tunnel release"},
    {"code": "W5", "name": "Wrist Fracture, Non-Operative", "body_region": "Wrist/Hand", "description": "Wrist fracture managed with immobilization"},
    {"code": "W6", "name": "Post-Operative Wrist Fracture Fixation (ORIF)", "body_region": "Wrist/Hand", "description": "Wrist fracture treated with open reduction internal fixation"},

    # Hip
    {"code": "H1", "name": "Hip Labral Tear, Non-Operative", "body_region": "Hip", "description": "Hip labral tear managed non-operatively"},
    {"code": "H2", "name": "Post-Operative Hip Arthroscopy", "body_region": "Hip", "description": "Patient has undergone hip arthroscopy"},
    {"code": "H3", "name": "Hip Osteoarthritis, Non-Operative", "body_region": "Hip", "description": "Post-traumatic hip osteoarthritis managed non-operatively"},
    {"code": "H4", "name": "Hip Fracture, Non-Operative", "body_region": "Hip", "description": "Hip fracture managed non-operatively"},
    {"code": "H5", "name": "Post-Operative Hip Fracture Fixation (ORIF)", "body_region": "Hip", "description": "Hip fracture treated with open reduction internal fixation"},
    {"code": "H6", "name": "Total Hip Arthroplasty (Primary)", "body_region": "Hip", "description": "Patient has undergone primary total hip arthroplasty"},

    # Knee
    {"code": "K1", "name": "Meniscus Tear, Non-Operative", "body_region": "Knee", "description": "Meniscal tear managed non-operatively"},
    {"code": "K2", "name": "Post-Operative Knee Arthroscopy", "body_region": "Knee", "description": "Patient has undergone knee arthroscopy"},
    {"code": "K3", "name": "ACL Tear, Non-Operative", "body_region": "Knee", "description": "ACL tear managed non-operatively"},
    {"code": "K4", "name": "Post-Operative ACL Reconstruction", "body_region": "Knee", "description": "Patient has undergone ACL reconstruction"},
    {"code": "K5", "name": "Knee Osteoarthritis, Non-Operative", "body_region": "Knee", "description": "Post-traumatic knee osteoarthritis managed non-operatively"},
    {"code": "K6", "name": "Tibial Plateau Fracture, Non-Operative", "body_region": "Knee", "description": "Tibial plateau fracture managed non-operatively"},
    {"code": "K7", "name": "Post-Operative Tibial Plateau Fracture Fixation (ORIF)", "body_region": "Knee", "description": "Tibial plateau fracture treated with ORIF"},
    {"code": "K8", "name": "Total Knee Arthroplasty (Primary)", "body_region": "Knee", "description": "Patient has undergone primary total knee arthroplasty"},

    # Foot/Ankle
    {"code": "F1", "name": "Ankle Sprain/Ligament Injury, Non-Operative (Structural)", "body_region": "Foot/Ankle", "description": "Ankle ligament injury with structural damage"},
    {"code": "F2", "name": "Post-Operative Ankle Ligament Reconstruction", "body_region": "Foot/Ankle", "description": "Patient has undergone ankle ligament reconstruction"},
    {"code": "F3", "name": "Achilles Tendon Injury, Non-Operative", "body_region": "Foot/Ankle", "description": "Achilles tendinopathy or tear managed non-operatively"},
    {"code": "F4", "name": "Post-Operative Achilles Tendon Repair", "body_region": "Foot/Ankle", "description": "Patient has undergone Achilles tendon repair"},
    {"code": "F5", "name": "Ankle Fracture, Non-Operative", "body_region": "Foot/Ankle", "description": "Ankle fracture managed non-operatively"},
    {"code": "F6", "name": "Post-Operative Ankle Fracture Fixation (ORIF)", "body_region": "Foot/Ankle", "description": "Ankle fracture treated with ORIF"},
    {"code": "F7", "name": "Ankle Osteoarthritis, Non-Operative", "body_region": "Foot/Ankle", "description": "Post-traumatic ankle osteoarthritis managed non-operatively"},
    {"code": "F8", "name": "Ankle Fusion (Arthrodesis)", "body_region": "Foot/Ankle", "description": "Patient has undergone ankle fusion"},
    {"code": "F9", "name": "Total Ankle Arthroplasty", "body_region": "Foot/Ankle", "description": "Patient has undergone total ankle arthroplasty"},
    {"code": "F10", "name": "Foot Fracture, Non-Operative", "body_region": "Foot/Ankle", "description": "Foot fracture managed non-operatively"},
    {"code": "F11", "name": "Post-Operative Foot Fracture Fixation (ORIF)", "body_region": "Foot/Ankle", "description": "Foot fracture treated with ORIF"},
    {"code": "F12", "name": "Plantar Fasciitis, Non-Operative (Structural)", "body_region": "Foot/Ankle", "description": "Plantar fasciitis with structural fascia damage"},
]


def insert_scenarios():
    """Insert scenario reference data."""
    print("\n=== Inserting Scenarios Reference Data ===")

    try:
        # Check if scenarios already exist
        response = supabase.table('scenarios').select('code').execute()
        existing_count = len(response.data) if response.data else 0

        if existing_count > 0:
            print(f"✓ {existing_count} scenarios already exist in database")
            return True

        # Insert scenarios
        for scenario in SCENARIOS_DATA:
            scenario['is_active'] = True

        response = supabase.table('scenarios').insert(SCENARIOS_DATA).execute()

        if response.data:
            print(f"✓ Inserted {len(response.data)} scenarios")
            return True
        else:
            print("✗ Failed to insert scenarios")
            return False

    except Exception as e:
        if 'does not exist' in str(e) or '42P01' in str(e):
            print("✗ scenarios table does not exist - run the SQL first")
            return False
        print(f"✗ Error inserting scenarios: {e}")
        return False


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    print("=" * 60)
    print("LCP Recommendations App - Supabase Setup")
    print("=" * 60)

    # Step 1: Check/Create tables
    tables_exist = create_tables()

    if not tables_exist:
        print("\n" + "=" * 60)
        print("ACTION REQUIRED:")
        print("1. Go to https://supabase.com/dashboard")
        print("2. Open your project")
        print("3. Go to SQL Editor")
        print("4. Paste and run the SQL shown above")
        print("5. Re-run this script")
        print("=" * 60)
        return

    # Step 2: Insert default rules
    insert_default_rules()

    # Step 3: Insert scenarios
    insert_scenarios()

    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Add SUPABASE_URL and SUPABASE_KEY to Render environment variables")
    print("2. Redeploy the app on Render")
    print("3. Test with a medical record document")


if __name__ == "__main__":
    main()
