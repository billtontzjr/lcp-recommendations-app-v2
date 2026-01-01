"""
Causation Analyzer - Applies Dr. Tontz's Injury Causation Protocol.

Uses Michael Freeman's three-prong test:
1. Temporal relationship
2. Biological plausibility
3. Absence of alternative explanation

Determines causation classification:
- CAUSAL: New condition caused by the injury
- AGGRAVATION: Permanent worsening of pre-existing condition
- EXACERBATION: Temporary worsening (excluded from LCP)
- SPRAIN_STRAIN: Self-limited injury (excluded from LCP)
- NOT_CAUSAL: Not related to injury (excluded from LCP)
"""

# Causation classifications
CAUSAL = "causal"
AGGRAVATION = "aggravation"
EXACERBATION = "exacerbation"
SPRAIN_STRAIN = "sprain_strain"
NOT_CAUSAL = "not_causal"

# Classifications that qualify for LCP recommendations
LCP_QUALIFYING = {CAUSAL, AGGRAVATION}


def get_causation_protocol_for_prompt() -> str:
    """
    Returns the causation protocol instructions for Claude's analysis prompt.
    """
    return """
## INJURY CAUSATION PROTOCOL (Dr. William Tontz Jr.)

You MUST apply causation analysis to every diagnosis before generating recommendations.
Only conditions that are CAUSALLY RELATED to the injury event qualify for Life Care Plan items.

### Framework: Michael Freeman's Three-Prong Test
For each diagnosis, evaluate:
1. **Temporal Relationship** - Was the complaint documented within the appropriate window?
2. **Biological Plausibility** - Is the mechanism of injury consistent with the diagnosis?
3. **Absence of Alternative Explanation** - Are there no better explanations (pre-existing, other events)?

### Temporal Relationship Rules
- WITHOUT distracting injuries: Complaints must appear within 30 days of DOI
- WITH distracting injuries (multiple fractures, rib trauma): Up to 90 days is reasonable
- Use ONLY contemporaneous provider records (ED notes, progress notes, operative reports, imaging, therapy notes)
- EXCLUDE retrospective histories, attorney letters, or later summaries

### Causation Classifications

**CAUSAL (Include in LCP):**
- New condition directly caused by the injury event
- Meets all three prongs of Freeman's test
- No pre-existing history of the condition

**AGGRAVATION (Include in LCP):**
- PERMANENT worsening of a pre-existing condition
- Evidenced by new objective findings OR durable escalation of care
- Post-event treatment frequency increased compared to baseline

**EXACERBATION (EXCLUDE from LCP):**
- TEMPORARY worsening of pre-existing condition
- Patient returns to baseline
- No lasting objective change
- Treatment is self-limiting

**SPRAIN/STRAIN (EXCLUDE from LCP):**
- Muscular injury, self-limited (6-12 weeks)
- If symptoms persist beyond 12 weeks, implies deeper diagnosis
- CANNOT coexist with deeper diagnoses (disc herniation, stenosis, fracture, labral/meniscal tear) in same body part

**NOT CAUSALLY RELATED (EXCLUDE from LCP):**
- Pre-existing condition without aggravation
- Complaint not documented within temporal window
- Alternative explanation more likely
- Non-orthopedic/non-spine conditions

### Condition-Specific Rules

**Cervical/Lumbar Herniated Disc:**
- Patients < 30 years: Rare; almost always event-related if new after injury
- Patients > 60 years: 20-30% asymptomatic prevalence; requires pre/post comparison
- Stability intervals (1-5 years symptom-free) strengthen causal link

**Radiculopathy:**
- Secondary to disc or stenosis
- Low prevalence in asymptomatic population
- New onset post-event is usually causal

**Stenosis:**
- Typically pre-existent
- Key question: Was it symptomatic pre-event?

**Facet Syndrome:**
- Plausible after extension/rotation trauma
- If absent pre-event and present post-event with diagnostic blocks = likely causal

**Joint Conditions (shoulder, hip, knee, ankle, wrist):**
- Assess pre- vs post-event complaints
- Compare objective imaging findings

### Compensable Consequence
Assess whether a primary injury caused a secondary condition (time-independent):
- Ankle fracture → altered gait → lumbar pain
- Immobilization → DVT (if clearly related to orthopedic treatment)
- Contralateral overuse → rotator cuff tear
- Assistive device use → wrist/shoulder pain

### Output Requirements
For each diagnosis in your analysis, you MUST determine:
1. Causation classification (causal, aggravation, exacerbation, sprain_strain, not_causal)
2. Brief causation rationale citing temporal relationship and evidence

**CRITICAL: Only generate scenario codes and LCP recommendations for diagnoses classified as "causal" or "aggravation".**
"""


def get_causation_json_schema() -> str:
    """
    Returns the JSON schema additions for causation in Claude's output.
    """
    return """
"diagnoses": [
    {
        "body_part": "Cervical Spine",
        "diagnosis": "C5-6 disc herniation",
        "structural": true,
        "date_documented": "7/10/2025",
        "causation": "causal",
        "causation_rationale": "New cervical radiculopathy documented in ED on 1/15/25, 2 days post-MVA. No prior cervical complaints in 5 years of records. Mechanism (rear-end collision) consistent with cervical disc injury."
    },
    {
        "body_part": "Lumbar Spine",
        "diagnosis": "L4-5 stenosis",
        "structural": true,
        "date_documented": "7/10/2025",
        "causation": "aggravation",
        "causation_rationale": "Pre-existing stenosis documented on 2019 MRI. Post-accident, patient required ESI series (none in prior 3 years). Permanent escalation of care indicates aggravation."
    },
    {
        "body_part": "Right Shoulder",
        "diagnosis": "Rotator cuff strain",
        "structural": false,
        "date_documented": "1/20/2025",
        "causation": "sprain_strain",
        "causation_rationale": "Muscular strain without structural tear on MRI. Expected resolution in 6-12 weeks. No LCP items required."
    }
]
"""


def filter_diagnoses_for_lcp(diagnoses: list) -> list:
    """
    Filter diagnoses to only include those qualifying for LCP.

    Args:
        diagnoses: List of diagnosis dicts with causation field

    Returns:
        List of diagnoses with causal or aggravation classification
    """
    return [
        d for d in diagnoses
        if d.get("causation", "").lower() in LCP_QUALIFYING
    ]


def get_excluded_diagnoses(diagnoses: list) -> list:
    """
    Get diagnoses excluded from LCP with reasons.

    Args:
        diagnoses: List of diagnosis dicts with causation field

    Returns:
        List of excluded diagnoses with exclusion reasons
    """
    excluded = []
    for d in diagnoses:
        causation = d.get("causation", "").lower()
        if causation not in LCP_QUALIFYING:
            reason = get_exclusion_reason(causation)
            excluded.append({
                **d,
                "exclusion_reason": reason
            })
    return excluded


def get_exclusion_reason(causation: str) -> str:
    """Get human-readable exclusion reason for causation type."""
    reasons = {
        EXACERBATION: "Temporary exacerbation - patient expected to return to baseline",
        SPRAIN_STRAIN: "Sprain/strain - self-limited injury (6-12 weeks), no ongoing care needed",
        NOT_CAUSAL: "Not causally related to the injury event",
        "": "Causation not determined"
    }
    return reasons.get(causation.lower(), f"Excluded due to {causation} classification")


def validate_sprain_strain_exclusivity(diagnoses: list) -> list:
    """
    Apply rule: Sprain/strain cannot coexist with deeper diagnoses in same body part.

    If both exist, remove the sprain/strain diagnosis.
    """
    # Group diagnoses by body part
    by_body_part = {}
    for d in diagnoses:
        bp = d.get("body_part", "").lower()
        if bp not in by_body_part:
            by_body_part[bp] = []
        by_body_part[bp].append(d)

    # Check each body part
    validated = []
    for body_part, dx_list in by_body_part.items():
        has_structural = any(d.get("structural", False) for d in dx_list)
        has_sprain_strain = any(
            d.get("causation", "").lower() == SPRAIN_STRAIN or
            "sprain" in d.get("diagnosis", "").lower() or
            "strain" in d.get("diagnosis", "").lower()
            for d in dx_list
        )

        if has_structural and has_sprain_strain:
            # Keep only the structural diagnoses, remove sprain/strain
            for d in dx_list:
                if d.get("structural", False):
                    validated.append(d)
                # Skip sprain/strain diagnoses when structural exists
        else:
            validated.extend(dx_list)

    return validated
