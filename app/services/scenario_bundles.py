"""
Scenario-to-Item Bundle Mappings for Life Care Plan Generation.

Each scenario (C1, C4, L2, etc.) maps to a fixed bundle of items.
Claude's job is to identify which scenarios apply based on medical records.
This module then deterministically maps scenarios to items with costs.
"""

# CPT Code Constants
CPT_OFFICE_VISIT = "99214"
CPT_CERVICAL_MRI = "72141"
CPT_CERVICAL_XRAY = "72040"
CPT_CERVICAL_CT = "72125"
CPT_THORACIC_MRI = "72146"
CPT_THORACIC_XRAY = "72070"
CPT_THORACIC_CT = "72128"
CPT_LUMBAR_MRI = "72148"
CPT_LUMBAR_XRAY = "72100"
CPT_LUMBAR_CT = "72131"
CPT_SHOULDER_MRI = "73221"
CPT_SHOULDER_XRAY = "73030"
CPT_ELBOW_MRI = "73221"
CPT_ELBOW_XRAY = "73080"
CPT_WRIST_MRI = "73221"
CPT_WRIST_XRAY = "73110"
CPT_HIP_MRI = "73721"
CPT_HIP_XRAY = "73501"
CPT_KNEE_MRI = "73721"
CPT_KNEE_XRAY = "73560"
CPT_ANKLE_MRI = "73721"
CPT_ANKLE_XRAY = "73600"
CPT_FOOT_MRI = "73721"
CPT_FOOT_XRAY = "73630"

# PT Codes
CPT_PT_EVAL = "97163"
CPT_PT_TREATMENT = ["97110", "97140", "97112", "97530"]

# Injection/Procedure Codes
CPT_CERVICAL_ESI = "62321"
CPT_THORACIC_ESI = "62321"
CPT_LUMBAR_ESI = "62323"
CPT_CERVICAL_RFA_PRIMARY = "64633"
CPT_CERVICAL_RFA_ADDON = "64634"
CPT_LUMBAR_RFA_PRIMARY = "64635"
CPT_LUMBAR_RFA_ADDON = "64636"

# Surgery Codes (DRG-based for facility fees)
DRG_CERVICAL_FUSION = "473"
DRG_LUMBAR_FUSION = "460"


def create_item(category, description, cpt, frequency, item_type, fee_type="PFR", units=1, note=""):
    """Helper to create a standardized item dictionary."""
    return {
        "category": category,
        "description": description,
        "cpt": cpt,
        "frequency": frequency,
        "type": item_type,  # "recurring" or "one_time"
        "fee_type": fee_type,  # "PFR", "APC", or "DRG"
        "units": units,
        "note": note
    }


# =============================================================================
# CERVICAL SPINE SCENARIOS
# =============================================================================

SCENARIO_C1 = {
    "code": "C1",
    "name": "Cervical Herniated Disc, Non-Operative",
    "description": "Structural cervical disc herniation managed non-operatively",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Cervical MRI", CPT_CERVICAL_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Cervical X-ray", CPT_CERVICAL_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy Evaluation", CPT_PT_EVAL, "every_5_years", "recurring"),
        create_item("Therapies", "Physical Therapy Treatment (24 visits)", CPT_PT_TREATMENT, "every_5_years", "recurring", units=24),
    ]
}

SCENARIO_C2 = {
    "code": "C2",
    "name": "Cervical Radiculopathy, No Prior ESI",
    "description": "Active cervical radiculopathy within one year, no prior ESI",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Physicians", "Pain Management Visit (for ESI)", CPT_OFFICE_VISIT, "one_time", "one_time"),
        create_item("Procedures/Hospitalizations/Surgery", "Cervical ESI - Professional Fee", CPT_CERVICAL_ESI, "one_time", "one_time", "PFR"),
        create_item("Procedures/Hospitalizations/Surgery", "Cervical ESI - Facility Fee", CPT_CERVICAL_ESI, "one_time", "one_time", "APC"),
        create_item("Diagnostic Testing", "Cervical MRI", CPT_CERVICAL_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Cervical X-ray", CPT_CERVICAL_XRAY, "every_2_years", "recurring"),
    ]
}

SCENARIO_C3 = {
    "code": "C3",
    "name": "Cervical Radiculopathy, Prior Beneficial ESI",
    "description": "Cervical radiculopathy with prior ESI that helped",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Physicians", "Pain Management Visit", CPT_OFFICE_VISIT, "3x_year", "recurring"),
        create_item("Procedures/Hospitalizations/Surgery", "Cervical ESI - Professional Fee", CPT_CERVICAL_ESI, "3x_year", "recurring", "PFR"),
        create_item("Procedures/Hospitalizations/Surgery", "Cervical ESI - Facility Fee", CPT_CERVICAL_ESI, "3x_year", "recurring", "APC"),
        create_item("Diagnostic Testing", "Cervical MRI", CPT_CERVICAL_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Cervical X-ray", CPT_CERVICAL_XRAY, "every_2_years", "recurring"),
    ]
}

SCENARIO_C4 = {
    "code": "C4",
    "name": "Cervical Facet Syndrome, Blocks Helped, No Prior RFA",
    "description": "Cervical facet syndrome with beneficial MBB, no prior RFA",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Physicians", "Pain Management Visit (for RFA)", CPT_OFFICE_VISIT, "one_time", "one_time"),
        create_item("Procedures/Hospitalizations/Surgery", "Cervical RFA - Professional Fee", [CPT_CERVICAL_RFA_PRIMARY, CPT_CERVICAL_RFA_ADDON, CPT_CERVICAL_RFA_ADDON], "one_time", "one_time", "PFR", note="3 levels bilateral"),
        create_item("Procedures/Hospitalizations/Surgery", "Cervical RFA - Facility Fee", CPT_CERVICAL_RFA_PRIMARY, "one_time", "one_time", "APC"),
        create_item("Diagnostic Testing", "Cervical MRI", CPT_CERVICAL_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Cervical X-ray", CPT_CERVICAL_XRAY, "every_2_years", "recurring"),
    ]
}

SCENARIO_C5 = {
    "code": "C5",
    "name": "Cervical Facet Syndrome, Prior Beneficial RFA",
    "description": "Cervical facet syndrome with prior RFA that helped",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Physicians", "Pain Management Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Procedures/Hospitalizations/Surgery", "Cervical RFA - Professional Fee", [CPT_CERVICAL_RFA_PRIMARY, CPT_CERVICAL_RFA_ADDON, CPT_CERVICAL_RFA_ADDON], "yearly", "recurring", "PFR"),
        create_item("Procedures/Hospitalizations/Surgery", "Cervical RFA - Facility Fee", CPT_CERVICAL_RFA_PRIMARY, "yearly", "recurring", "APC"),
        create_item("Diagnostic Testing", "Cervical MRI", CPT_CERVICAL_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Cervical X-ray", CPT_CERVICAL_XRAY, "every_2_years", "recurring"),
    ]
}

SCENARIO_C6 = {
    "code": "C6",
    "name": "Post-Operative Cervical Fusion or Disc Replacement",
    "description": "Patient has undergone ACDF or cervical disc replacement",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Cervical MRI", CPT_CERVICAL_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Cervical X-ray", CPT_CERVICAL_XRAY, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Cervical CT Scan", CPT_CERVICAL_CT, "every_5_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (24 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=24),
    ]
}


# =============================================================================
# THORACIC SPINE SCENARIOS
# =============================================================================

SCENARIO_T1 = {
    "code": "T1",
    "name": "Thoracic Axial/Facet Pain, Non-Operative",
    "description": "Thoracic axial pain managed conservatively",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Thoracic MRI", CPT_THORACIC_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Thoracic X-ray", CPT_THORACIC_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=12),
    ]
}

SCENARIO_T2 = {
    "code": "T2",
    "name": "Thoracic Radiculopathy, Prior Beneficial ESI",
    "description": "Thoracic radiculopathy with prior ESI that helped",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Physicians", "Pain Management Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Procedures/Hospitalizations/Surgery", "Thoracic ESI - Professional Fee", CPT_THORACIC_ESI, "yearly", "recurring", "PFR"),
        create_item("Procedures/Hospitalizations/Surgery", "Thoracic ESI - Facility Fee", CPT_THORACIC_ESI, "yearly", "recurring", "APC"),
        create_item("Diagnostic Testing", "Thoracic MRI", CPT_THORACIC_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Thoracic X-ray", CPT_THORACIC_XRAY, "every_2_years", "recurring"),
    ]
}

SCENARIO_T3 = {
    "code": "T3",
    "name": "Thoracic Compression Fracture, Non-Operative",
    "description": "Thoracic compression fracture managed conservatively",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Thoracic MRI", CPT_THORACIC_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Thoracic X-ray", CPT_THORACIC_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=18),
        create_item("Durable Medical Equipment", "TLSO Brace", "L0456", "every_5_years", "recurring"),
    ]
}

SCENARIO_T4 = {
    "code": "T4",
    "name": "Post-Operative Thoracic Fusion",
    "description": "Patient has undergone thoracic spinal fusion",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Thoracic MRI", CPT_THORACIC_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Thoracic X-ray", CPT_THORACIC_XRAY, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Thoracic CT Scan", CPT_THORACIC_CT, "every_5_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (24 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=24),
    ]
}


# =============================================================================
# LUMBAR SPINE SCENARIOS
# =============================================================================

SCENARIO_L1 = {
    "code": "L1",
    "name": "Lumbar Disc Herniation, Non-Operative",
    "description": "Lumbar disc herniation managed non-operatively",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Lumbar MRI", CPT_LUMBAR_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Lumbar X-ray", CPT_LUMBAR_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy Evaluation", CPT_PT_EVAL, "every_5_years", "recurring"),
        create_item("Therapies", "Physical Therapy Treatment (24 visits)", CPT_PT_TREATMENT, "every_5_years", "recurring", units=24),
    ]
}

SCENARIO_L2 = {
    "code": "L2",
    "name": "Lumbar Radiculopathy, Prior Beneficial ESI",
    "description": "Lumbar radiculopathy with prior ESI that helped",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Physicians", "Pain Management Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Procedures/Hospitalizations/Surgery", "Lumbar ESI - Professional Fee", CPT_LUMBAR_ESI, "yearly", "recurring", "PFR"),
        create_item("Procedures/Hospitalizations/Surgery", "Lumbar ESI - Facility Fee", CPT_LUMBAR_ESI, "yearly", "recurring", "APC"),
        create_item("Diagnostic Testing", "Lumbar MRI", CPT_LUMBAR_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Lumbar X-ray", CPT_LUMBAR_XRAY, "every_2_years", "recurring"),
    ]
}

SCENARIO_L3 = {
    "code": "L3",
    "name": "Lumbar Facet Syndrome, Blocks Helped, No Prior RFA",
    "description": "Lumbar facet syndrome with beneficial MBB, no prior RFA",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Physicians", "Pain Management Visit (for RFA)", CPT_OFFICE_VISIT, "one_time", "one_time"),
        create_item("Procedures/Hospitalizations/Surgery", "Lumbar RFA - Professional Fee", [CPT_LUMBAR_RFA_PRIMARY, CPT_LUMBAR_RFA_ADDON, CPT_LUMBAR_RFA_ADDON], "one_time", "one_time", "PFR", note="3 levels bilateral"),
        create_item("Procedures/Hospitalizations/Surgery", "Lumbar RFA - Facility Fee", CPT_LUMBAR_RFA_PRIMARY, "one_time", "one_time", "APC"),
        create_item("Diagnostic Testing", "Lumbar MRI", CPT_LUMBAR_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Lumbar X-ray", CPT_LUMBAR_XRAY, "every_2_years", "recurring"),
    ]
}

SCENARIO_L4 = {
    "code": "L4",
    "name": "Lumbar Facet Syndrome, Prior Beneficial RFA",
    "description": "Lumbar facet syndrome with prior RFA that helped",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Physicians", "Pain Management Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Procedures/Hospitalizations/Surgery", "Lumbar RFA - Professional Fee", [CPT_LUMBAR_RFA_PRIMARY, CPT_LUMBAR_RFA_ADDON, CPT_LUMBAR_RFA_ADDON], "yearly", "recurring", "PFR"),
        create_item("Procedures/Hospitalizations/Surgery", "Lumbar RFA - Facility Fee", CPT_LUMBAR_RFA_PRIMARY, "yearly", "recurring", "APC"),
        create_item("Diagnostic Testing", "Lumbar MRI", CPT_LUMBAR_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Lumbar X-ray", CPT_LUMBAR_XRAY, "every_2_years", "recurring"),
    ]
}

SCENARIO_L5 = {
    "code": "L5",
    "name": "Post-Operative Lumbar Discectomy",
    "description": "Patient has undergone lumbar discectomy",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Lumbar MRI", CPT_LUMBAR_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Lumbar X-ray", CPT_LUMBAR_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (24 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=24),
        create_item("Therapies", "Long-term Physical Therapy (24 visits)", CPT_PT_TREATMENT, "every_2_years", "recurring", units=24),
    ]
}

SCENARIO_L6 = {
    "code": "L6",
    "name": "Post-Operative Lumbar Fusion",
    "description": "Patient has undergone lumbar spinal fusion",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Lumbar MRI", CPT_LUMBAR_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Lumbar X-ray", CPT_LUMBAR_XRAY, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Lumbar CT Scan", CPT_LUMBAR_CT, "every_5_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (24 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=24),
    ]
}

SCENARIO_L7 = {
    "code": "L7",
    "name": "Lumbar Radiculopathy, No Prior ESI",
    "description": "Active lumbar radiculopathy within one year, no prior ESI",
    "items": [
        create_item("Physicians", "Spine Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Physicians", "Pain Management Visit (for ESI)", CPT_OFFICE_VISIT, "one_time", "one_time"),
        create_item("Procedures/Hospitalizations/Surgery", "Lumbar ESI - Professional Fee", CPT_LUMBAR_ESI, "one_time", "one_time", "PFR"),
        create_item("Procedures/Hospitalizations/Surgery", "Lumbar ESI - Facility Fee", CPT_LUMBAR_ESI, "one_time", "one_time", "APC"),
        create_item("Diagnostic Testing", "Lumbar MRI", CPT_LUMBAR_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Lumbar X-ray", CPT_LUMBAR_XRAY, "every_2_years", "recurring"),
    ]
}


# =============================================================================
# SHOULDER SCENARIOS
# =============================================================================

SCENARIO_S1 = {
    "code": "S1",
    "name": "Rotator Cuff Tendinopathy or Partial Tear, Non-Operative",
    "description": "Rotator cuff partial tear managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Shoulder Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Shoulder MRI", CPT_SHOULDER_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Shoulder X-ray", CPT_SHOULDER_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_2_years", "recurring", units=18),
    ]
}

SCENARIO_S2 = {
    "code": "S2",
    "name": "Full-Thickness Rotator Cuff Tear, Non-Operative",
    "description": "Full-thickness rotator cuff tear managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Shoulder Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Shoulder MRI", CPT_SHOULDER_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Shoulder X-ray", CPT_SHOULDER_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (24 visits)", CPT_PT_TREATMENT, "every_2_years", "recurring", units=24),
        create_item("Procedures/Hospitalizations/Surgery", "Subacromial Injection", "20610", "yearly", "recurring"),
    ]
}

SCENARIO_S3 = {
    "code": "S3",
    "name": "Post-Operative Rotator Cuff Repair",
    "description": "Patient has undergone rotator cuff repair",
    "items": [
        create_item("Physicians", "Orthopedic Shoulder Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Shoulder MRI", CPT_SHOULDER_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Shoulder X-ray", CPT_SHOULDER_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
        create_item("Therapies", "Long-term Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=18),
    ]
}

SCENARIO_S4 = {
    "code": "S4",
    "name": "Shoulder Labral Tear, Non-Operative",
    "description": "Glenoid labral tear managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Shoulder Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Shoulder MRI", CPT_SHOULDER_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Shoulder X-ray", CPT_SHOULDER_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_2_years", "recurring", units=18),
    ]
}

SCENARIO_S5 = {
    "code": "S5",
    "name": "Post-Operative Labral Repair",
    "description": "Patient has undergone labral repair",
    "items": [
        create_item("Physicians", "Orthopedic Shoulder Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Shoulder MRI", CPT_SHOULDER_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Shoulder X-ray", CPT_SHOULDER_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
        create_item("Therapies", "Long-term Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=18),
    ]
}

SCENARIO_S6 = {
    "code": "S6",
    "name": "Shoulder Arthroplasty",
    "description": "Patient has undergone shoulder replacement",
    "items": [
        create_item("Physicians", "Orthopedic Shoulder Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Shoulder MRI", CPT_SHOULDER_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Shoulder X-ray", CPT_SHOULDER_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
    ]
}


# =============================================================================
# ELBOW SCENARIOS
# =============================================================================

SCENARIO_E1 = {
    "code": "E1",
    "name": "Elbow Tendinopathy, Non-Operative",
    "description": "Overuse or traumatic elbow tendinopathy managed conservatively",
    "items": [
        create_item("Physicians", "Orthopedic Elbow Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Elbow MRI", CPT_ELBOW_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Elbow X-ray", CPT_ELBOW_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=12),
    ]
}

SCENARIO_E2 = {
    "code": "E2",
    "name": "Post-Operative Elbow Surgery",
    "description": "Elbow surgery (ulnar nerve transposition, tendon repair)",
    "items": [
        create_item("Physicians", "Orthopedic Elbow Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Elbow MRI", CPT_ELBOW_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Elbow X-ray", CPT_ELBOW_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (18 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=18),
    ]
}

SCENARIO_E3 = {
    "code": "E3",
    "name": "Cubital Tunnel Syndrome, Non-Surgical",
    "description": "Ulnar nerve compression at the elbow managed without surgery",
    "items": [
        create_item("Physicians", "Orthopedic/Hand Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Durable Medical Equipment", "Night-time Elbow Splint", "L3760", "every_4_years", "recurring"),
        create_item("Therapies", "Occupational Therapy (12 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=12),
    ]
}

SCENARIO_E4 = {
    "code": "E4",
    "name": "Post-Operative Cubital Tunnel Release",
    "description": "Surgical decompression of the ulnar nerve at the elbow",
    "items": [
        create_item("Physicians", "Orthopedic/Hand Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Therapies", "Post-Operative Occupational Therapy (18 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=18),
    ]
}

SCENARIO_E5 = {
    "code": "E5",
    "name": "Elbow Fracture/Dislocation, Non-Operative",
    "description": "Elbow fracture or dislocation managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Elbow Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Elbow MRI", CPT_ELBOW_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Elbow X-ray", CPT_ELBOW_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
    ]
}

SCENARIO_E6 = {
    "code": "E6",
    "name": "Post-Operative Elbow Fracture Fixation (ORIF)",
    "description": "Elbow fracture treated with open reduction internal fixation",
    "items": [
        create_item("Physicians", "Orthopedic Elbow Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Elbow MRI", CPT_ELBOW_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Elbow X-ray", CPT_ELBOW_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
    ]
}


# =============================================================================
# WRIST/HAND SCENARIOS
# =============================================================================

SCENARIO_W1 = {
    "code": "W1",
    "name": "Wrist/Hand Tendinopathy or Mild Carpal Tunnel, Non-Operative",
    "description": "Wrist or hand tendinopathy or mild carpal tunnel syndrome managed conservatively",
    "items": [
        create_item("Physicians", "Orthopedic or Hand Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Durable Medical Equipment", "Wrist Splint", "L3908", "every_4_years", "recurring"),
        create_item("Therapies", "Occupational Therapy (12 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=12),
    ]
}

SCENARIO_W2 = {
    "code": "W2",
    "name": "Post-Operative Tendon Repair of the Wrist/Hand",
    "description": "Surgical repair of wrist/hand tendons",
    "items": [
        create_item("Physicians", "Hand Surgeon Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Wrist/Hand MRI", CPT_WRIST_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Wrist/Hand X-ray", CPT_WRIST_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Occupational Therapy (18 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=18),
    ]
}

SCENARIO_W3 = {
    "code": "W3",
    "name": "Carpal Tunnel Syndrome, Non-Surgical",
    "description": "Median nerve compression at the wrist managed without surgery",
    "items": [
        create_item("Physicians", "Hand Surgeon Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Durable Medical Equipment", "Wrist Splint", "L3908", "every_4_years", "recurring"),
        create_item("Therapies", "Occupational Therapy (12 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=12),
        create_item("Procedures/Hospitalizations/Surgery", "Carpal Tunnel Injection", "20526", "yearly", "recurring"),
    ]
}

SCENARIO_W4 = {
    "code": "W4",
    "name": "Post-Operative Carpal Tunnel Release",
    "description": "Open or endoscopic carpal tunnel release",
    "items": [
        create_item("Physicians", "Hand Surgeon Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Therapies", "Post-Operative Occupational Therapy (18 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=18),
    ]
}

SCENARIO_W5 = {
    "code": "W5",
    "name": "Wrist Fracture, Non-Operative",
    "description": "Distal radius fracture, scaphoid fracture, or other wrist fracture managed with immobilization",
    "items": [
        create_item("Physicians", "Orthopedic or Hand Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Wrist MRI", CPT_WRIST_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Wrist X-ray", CPT_WRIST_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=18),
        create_item("Durable Medical Equipment", "Wrist Splint", "L3908", "every_4_years", "recurring"),
    ]
}

SCENARIO_W6 = {
    "code": "W6",
    "name": "Post-Operative Wrist Fracture Fixation (ORIF)",
    "description": "Distal radius fracture treated with open reduction internal fixation",
    "items": [
        create_item("Physicians", "Orthopedic or Hand Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Wrist MRI", CPT_WRIST_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Wrist X-ray", CPT_WRIST_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Occupational Therapy (24 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=24),
    ]
}


# =============================================================================
# KNEE SCENARIOS
# =============================================================================

SCENARIO_K1 = {
    "code": "K1",
    "name": "Meniscus Tear, Non-Operative",
    "description": "Meniscal tear managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Knee Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Knee MRI", CPT_KNEE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Knee X-ray", CPT_KNEE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
        create_item("Procedures/Hospitalizations/Surgery", "Knee Injection", "20610", "yearly", "recurring"),
        create_item("Durable Medical Equipment", "Hinged Knee Brace", "L1832", "every_4_years", "recurring"),
    ]
}

SCENARIO_K2 = {
    "code": "K2",
    "name": "Post-Operative Knee Arthroscopy",
    "description": "Patient has undergone knee arthroscopy (meniscectomy or meniscal repair)",
    "items": [
        create_item("Physicians", "Orthopedic Knee Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Knee MRI", CPT_KNEE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Knee X-ray", CPT_KNEE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (18 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=18),
        create_item("Therapies", "Long-term Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=12),
    ]
}

SCENARIO_K3 = {
    "code": "K3",
    "name": "ACL Tear, Non-Operative",
    "description": "ACL tear managed non-operatively with rehabilitation and bracing",
    "items": [
        create_item("Physicians", "Orthopedic Knee Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Knee MRI", CPT_KNEE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Knee X-ray", CPT_KNEE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (24 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=24),
        create_item("Durable Medical Equipment", "Functional ACL Brace", "L1845", "every_4_years", "recurring"),
    ]
}

SCENARIO_K4 = {
    "code": "K4",
    "name": "Post-Operative ACL Reconstruction",
    "description": "Patient has undergone ACL reconstruction",
    "items": [
        create_item("Physicians", "Orthopedic Knee Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Knee MRI", CPT_KNEE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Knee X-ray", CPT_KNEE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (42 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=42),
        create_item("Therapies", "Long-term Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
        create_item("Durable Medical Equipment", "Functional ACL Brace", "L1845", "every_4_years", "recurring"),
    ]
}

SCENARIO_K5 = {
    "code": "K5",
    "name": "Knee Osteoarthritis, Non-Operative",
    "description": "Post-traumatic knee osteoarthritis managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Knee Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Knee MRI", CPT_KNEE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Knee X-ray", CPT_KNEE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
        create_item("Procedures/Hospitalizations/Surgery", "Knee Injection", "20610", "2x_year", "recurring"),
        create_item("Durable Medical Equipment", "Unloader Knee Brace", "L1843", "every_4_years", "recurring"),
        create_item("Durable Medical Equipment", "Cane", "E0100", "every_5_years", "recurring"),
    ]
}

SCENARIO_K6 = {
    "code": "K6",
    "name": "Tibial Plateau Fracture, Non-Operative",
    "description": "Tibial plateau fracture managed non-operatively with protected weight-bearing",
    "items": [
        create_item("Physicians", "Orthopedic Knee Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Knee MRI", CPT_KNEE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Knee X-ray", CPT_KNEE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (24 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=24),
        create_item("Durable Medical Equipment", "Hinged Knee Brace", "L1832", "every_4_years", "recurring"),
    ]
}

SCENARIO_K7 = {
    "code": "K7",
    "name": "Post-Operative Tibial Plateau Fracture Fixation (ORIF)",
    "description": "Tibial plateau fracture treated with open reduction internal fixation",
    "items": [
        create_item("Physicians", "Orthopedic Knee Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Knee MRI", CPT_KNEE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Knee X-ray", CPT_KNEE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
        create_item("Therapies", "Long-term Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
    ]
}

SCENARIO_K8 = {
    "code": "K8",
    "name": "Total Knee Arthroplasty (Primary)",
    "description": "Patient has undergone primary total knee arthroplasty",
    "items": [
        create_item("Physicians", "Orthopedic Knee Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Knee MRI", CPT_KNEE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Knee X-ray", CPT_KNEE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
        create_item("Therapies", "Long-term Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=12),
    ]
}


# =============================================================================
# HIP SCENARIOS
# =============================================================================

SCENARIO_H1 = {
    "code": "H1",
    "name": "Hip Labral Tear, Non-Operative",
    "description": "Hip labral tear managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Hip Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Hip MRI", CPT_HIP_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Hip X-ray", CPT_HIP_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
        create_item("Procedures/Hospitalizations/Surgery", "Hip Injection", "20610", "yearly", "recurring"),
    ]
}

SCENARIO_H2 = {
    "code": "H2",
    "name": "Post-Operative Hip Arthroscopy",
    "description": "Patient has undergone hip arthroscopy for labral repair/debridement or FAI correction",
    "items": [
        create_item("Physicians", "Orthopedic Hip Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Hip MRI", CPT_HIP_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Hip X-ray", CPT_HIP_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
        create_item("Therapies", "Long-term Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=18),
    ]
}

SCENARIO_H3 = {
    "code": "H3",
    "name": "Hip Osteoarthritis, Non-Operative",
    "description": "Post-traumatic hip osteoarthritis managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Hip Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Hip MRI", CPT_HIP_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Hip X-ray", CPT_HIP_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
        create_item("Procedures/Hospitalizations/Surgery", "Hip Injection", "20610", "yearly", "recurring"),
        create_item("Durable Medical Equipment", "Cane", "E0100", "every_5_years", "recurring"),
    ]
}

SCENARIO_H4 = {
    "code": "H4",
    "name": "Hip Fracture, Non-Operative",
    "description": "Hip fracture managed non-operatively with protected weight-bearing",
    "items": [
        create_item("Physicians", "Orthopedic Hip Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Hip MRI", CPT_HIP_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Hip X-ray", CPT_HIP_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (24 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=24),
        create_item("Durable Medical Equipment", "Assistive Device", "E0100", "every_5_years", "recurring"),
    ]
}

SCENARIO_H5 = {
    "code": "H5",
    "name": "Post-Operative Hip Fracture Fixation (ORIF)",
    "description": "Hip fracture treated with open reduction internal fixation",
    "items": [
        create_item("Physicians", "Orthopedic Hip Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Hip MRI", CPT_HIP_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Hip X-ray", CPT_HIP_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
        create_item("Therapies", "Long-term Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
    ]
}

SCENARIO_H6 = {
    "code": "H6",
    "name": "Total Hip Arthroplasty (Primary)",
    "description": "Patient has undergone primary total hip arthroplasty",
    "items": [
        create_item("Physicians", "Orthopedic Hip Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Hip MRI", CPT_HIP_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Hip X-ray", CPT_HIP_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
        create_item("Therapies", "Long-term Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=12),
    ]
}


# =============================================================================
# FOOT AND ANKLE SCENARIOS
# =============================================================================

SCENARIO_F1 = {
    "code": "F1",
    "name": "Ankle Sprain/Ligament Injury, Non-Operative (Structural)",
    "description": "Ankle ligament injury with structural damage (complete tear, chronic instability)",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Ankle MRI", CPT_ANKLE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Ankle X-ray", CPT_ANKLE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
        create_item("Durable Medical Equipment", "Ankle Brace", "L1906", "every_3_years", "recurring"),
    ]
}

SCENARIO_F2 = {
    "code": "F2",
    "name": "Post-Operative Ankle Ligament Reconstruction",
    "description": "Patient has undergone ankle ligament reconstruction (Brostrom repair or anatomic reconstruction)",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Ankle MRI", CPT_ANKLE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Ankle X-ray", CPT_ANKLE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
        create_item("Therapies", "Long-term Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=12),
        create_item("Durable Medical Equipment", "Ankle Brace", "L1906", "every_4_years", "recurring"),
    ]
}

SCENARIO_F3 = {
    "code": "F3",
    "name": "Achilles Tendon Injury, Non-Operative",
    "description": "Achilles tendinopathy, partial tear, or complete rupture managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Ankle MRI", CPT_ANKLE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Ankle X-ray", CPT_ANKLE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
        create_item("Durable Medical Equipment", "Heel Lift or Orthotic", "L3000", "every_3_years", "recurring"),
    ]
}

SCENARIO_F4 = {
    "code": "F4",
    "name": "Post-Operative Achilles Tendon Repair",
    "description": "Patient has undergone surgical repair of a complete Achilles tendon rupture",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Ankle MRI", CPT_ANKLE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Ankle X-ray", CPT_ANKLE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (42 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=42),
        create_item("Therapies", "Long-term Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=12),
        create_item("Durable Medical Equipment", "Heel Lift or Custom Orthotic", "L3000", "every_3_years", "recurring"),
    ]
}

SCENARIO_F5 = {
    "code": "F5",
    "name": "Ankle Fracture, Non-Operative",
    "description": "Ankle fracture managed non-operatively with immobilization",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Ankle MRI", CPT_ANKLE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Ankle X-ray", CPT_ANKLE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
        create_item("Durable Medical Equipment", "Ankle Brace or Custom Orthotic", "L1906", "every_4_years", "recurring"),
    ]
}

SCENARIO_F6 = {
    "code": "F6",
    "name": "Post-Operative Ankle Fracture Fixation (ORIF)",
    "description": "Ankle fracture treated with open reduction internal fixation",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Ankle MRI", CPT_ANKLE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Ankle X-ray", CPT_ANKLE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
        create_item("Therapies", "Long-term Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=12),
    ]
}

SCENARIO_F7 = {
    "code": "F7",
    "name": "Ankle Osteoarthritis, Non-Operative",
    "description": "Post-traumatic ankle osteoarthritis managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Ankle MRI", CPT_ANKLE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Ankle X-ray", CPT_ANKLE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=12),
        create_item("Procedures/Hospitalizations/Surgery", "Ankle Injection", "20605", "yearly", "recurring"),
        create_item("Durable Medical Equipment", "Arizona Brace or Custom AFO", "L1970", "every_4_years", "recurring"),
        create_item("Durable Medical Equipment", "Rocker-bottom Shoe Modification", "L3215", "every_3_years", "recurring"),
    ]
}

SCENARIO_F8 = {
    "code": "F8",
    "name": "Ankle Fusion (Arthrodesis)",
    "description": "Patient has undergone ankle fusion for end-stage post-traumatic ankle arthritis",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Ankle MRI", CPT_ANKLE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Ankle X-ray", CPT_ANKLE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (24 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=24),
        create_item("Therapies", "Long-term Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=12),
        create_item("Durable Medical Equipment", "Rocker-bottom Shoe Modification", "L3215", "every_3_years", "recurring"),
    ]
}

SCENARIO_F9 = {
    "code": "F9",
    "name": "Total Ankle Arthroplasty",
    "description": "Patient has undergone total ankle arthroplasty for end-stage post-traumatic ankle arthritis",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Ankle MRI", CPT_ANKLE_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Ankle X-ray", CPT_ANKLE_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (30 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=30),
        create_item("Therapies", "Long-term Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_4_years", "recurring", units=12),
    ]
}

SCENARIO_F10 = {
    "code": "F10",
    "name": "Foot Fracture, Non-Operative",
    "description": "Foot fracture (metatarsal, calcaneus, navicular, cuboid, or Lisfranc) managed non-operatively",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Foot MRI", CPT_FOOT_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Foot X-ray", CPT_FOOT_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Physical Therapy (18 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=18),
        create_item("Durable Medical Equipment", "Custom Orthotic or Arch Support", "L3000", "every_3_years", "recurring"),
        create_item("Durable Medical Equipment", "Shoe Modification", "L3215", "every_3_years", "recurring"),
    ]
}

SCENARIO_F11 = {
    "code": "F11",
    "name": "Post-Operative Foot Fracture Fixation (ORIF)",
    "description": "Foot fracture (calcaneus, Lisfranc, or complex metatarsal) treated with ORIF",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle Specialist Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Diagnostic Testing", "Foot MRI", CPT_FOOT_MRI, "every_2_years", "recurring"),
        create_item("Diagnostic Testing", "Foot X-ray", CPT_FOOT_XRAY, "every_2_years", "recurring"),
        create_item("Therapies", "Post-Operative Physical Therapy (24 visits)", CPT_PT_TREATMENT, "one_time", "one_time", units=24),
        create_item("Therapies", "Long-term Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=12),
        create_item("Durable Medical Equipment", "Custom Orthotic", "L3000", "every_3_years", "recurring"),
    ]
}

SCENARIO_F12 = {
    "code": "F12",
    "name": "Plantar Fasciitis, Non-Operative (Structural)",
    "description": "Plantar fasciitis with structural fascia damage requiring long-term management",
    "items": [
        create_item("Physicians", "Orthopedic Foot and Ankle or Podiatry Office Visit", CPT_OFFICE_VISIT, "yearly", "recurring"),
        create_item("Therapies", "Physical Therapy (12 visits)", CPT_PT_TREATMENT, "every_3_years", "recurring", units=12),
        create_item("Durable Medical Equipment", "Custom Orthotic or Arch Support", "L3000", "every_3_years", "recurring"),
        create_item("Durable Medical Equipment", "Night Splint", "L4396", "every_4_years", "recurring"),
        create_item("Procedures/Hospitalizations/Surgery", "Plantar Fascia Injection", "20550", "yearly", "recurring"),
    ]
}


# =============================================================================
# MASTER SCENARIO LOOKUP
# =============================================================================

SCENARIO_BUNDLES = {
    # Cervical Spine (C1-C6)
    "C1": SCENARIO_C1,
    "C2": SCENARIO_C2,
    "C3": SCENARIO_C3,
    "C4": SCENARIO_C4,
    "C5": SCENARIO_C5,
    "C6": SCENARIO_C6,
    # Thoracic Spine (T1-T4)
    "T1": SCENARIO_T1,
    "T2": SCENARIO_T2,
    "T3": SCENARIO_T3,
    "T4": SCENARIO_T4,
    # Lumbar Spine (L1-L7)
    "L1": SCENARIO_L1,
    "L2": SCENARIO_L2,
    "L3": SCENARIO_L3,
    "L4": SCENARIO_L4,
    "L5": SCENARIO_L5,
    "L6": SCENARIO_L6,
    "L7": SCENARIO_L7,
    # Shoulder (S1-S6)
    "S1": SCENARIO_S1,
    "S2": SCENARIO_S2,
    "S3": SCENARIO_S3,
    "S4": SCENARIO_S4,
    "S5": SCENARIO_S5,
    "S6": SCENARIO_S6,
    # Elbow (E1-E6)
    "E1": SCENARIO_E1,
    "E2": SCENARIO_E2,
    "E3": SCENARIO_E3,
    "E4": SCENARIO_E4,
    "E5": SCENARIO_E5,
    "E6": SCENARIO_E6,
    # Wrist/Hand (W1-W6)
    "W1": SCENARIO_W1,
    "W2": SCENARIO_W2,
    "W3": SCENARIO_W3,
    "W4": SCENARIO_W4,
    "W5": SCENARIO_W5,
    "W6": SCENARIO_W6,
    # Hip (H1-H6)
    "H1": SCENARIO_H1,
    "H2": SCENARIO_H2,
    "H3": SCENARIO_H3,
    "H4": SCENARIO_H4,
    "H5": SCENARIO_H5,
    "H6": SCENARIO_H6,
    # Knee (K1-K8)
    "K1": SCENARIO_K1,
    "K2": SCENARIO_K2,
    "K3": SCENARIO_K3,
    "K4": SCENARIO_K4,
    "K5": SCENARIO_K5,
    "K6": SCENARIO_K6,
    "K7": SCENARIO_K7,
    "K8": SCENARIO_K8,
    # Foot/Ankle (F1-F12)
    "F1": SCENARIO_F1,
    "F2": SCENARIO_F2,
    "F3": SCENARIO_F3,
    "F4": SCENARIO_F4,
    "F5": SCENARIO_F5,
    "F6": SCENARIO_F6,
    "F7": SCENARIO_F7,
    "F8": SCENARIO_F8,
    "F9": SCENARIO_F9,
    "F10": SCENARIO_F10,
    "F11": SCENARIO_F11,
    "F12": SCENARIO_F12,
}


def get_scenario(code: str) -> dict:
    """Get scenario bundle by code."""
    return SCENARIO_BUNDLES.get(code.upper())


def get_all_scenario_codes() -> list:
    """Get list of all available scenario codes."""
    return list(SCENARIO_BUNDLES.keys())


def get_scenario_summary() -> dict:
    """Get summary of all scenarios for Claude prompt."""
    return {
        code: {
            "name": bundle["name"],
            "description": bundle["description"]
        }
        for code, bundle in SCENARIO_BUNDLES.items()
    }
