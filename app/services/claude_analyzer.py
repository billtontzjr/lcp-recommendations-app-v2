"""
Claude API service for medical record analysis - Phase 1.

This module handles the AI-driven clinical decision phase:
- Analyzes medical records to identify injuries/diagnoses
- Applies decision trees to match clinical scenarios
- Outputs scenario codes (C1, C4, L2, etc.)

The scenario codes are then mapped to item bundles by scenario_mapper.py (Phase 2).
"""

import os
import json
from anthropic import Anthropic
from app.services.scenario_bundles import get_scenario_summary


def get_scenario_list_for_prompt() -> str:
    """Generate scenario list for Claude prompt."""
    scenarios = get_scenario_summary()
    lines = []
    for code, info in sorted(scenarios.items()):
        lines.append(f"- **{code}**: {info['name']} - {info['description']}")
    return "\n".join(lines)


def analyze_medical_records(medical_summary: str, patient_info: dict) -> dict:
    """
    Phase 1: Analyze medical records and identify applicable scenarios.

    Args:
        medical_summary: Text content from the medical records document
        patient_info: Dict with patient name, DOB, life expectancy, etc.

    Returns:
        Dict with:
        - scenarios: List of scenario codes (e.g., ["C1", "C4"])
        - diagnoses: List of identified diagnoses with body parts
        - rationales: Dict mapping scenario code to patient-specific rationale
        - summary: Brief summary of injuries and care needs
    """
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    scenario_list = get_scenario_list_for_prompt()

    system_prompt = f"""You are a medical expert assistant helping Dr. William Tontz, MD, CLCP identify applicable clinical scenarios for Life Care Plans.

Your task is to analyze medical records and identify which predefined clinical scenarios apply to this patient.

## Available Clinical Scenarios:
{scenario_list}

## Decision Tree for Scenario Selection:

### SPINE ANALYSIS:
For each spine region (cervical, thoracic, lumbar):

1. **Is there a STRUCTURAL diagnosis?** (herniation, stenosis, fracture, facet syndrome, radiculopathy)
   - NO structural finding → Skip this region (sprains/strains don't need LCP items)
   - YES → Continue to step 2

2. **Check for prior surgery:**
   - Cervical fusion/ACDF/disc replacement → C6
   - Thoracic fusion → T4
   - Lumbar fusion → L6
   - Lumbar discectomy → L5

3. **If no surgery, check for facet/RFA history:**
   - Facet blocks/MBB performed with benefit + NO prior RFA → One-time RFA (C4, L3)
   - Prior RFA with benefit → Annual RFA (C5, L4)

4. **If no surgery or RFA, check for radiculopathy/ESI:**
   - Active radiculopathy + NO prior ESI → One-time ESI (C2, L7)
   - Prior ESI with benefit → Annual ESI (C3, L2, T2)

5. **If structural diagnosis but none of above:**
   - Cervical disc/stenosis → C1
   - Thoracic pain → T1
   - Thoracic compression fracture → T3
   - Lumbar disc → L1

### UPPER EXTREMITY ANALYSIS:
- Rotator cuff partial tear, non-op → S1
- Rotator cuff full tear, non-op → S2
- Post-op rotator cuff repair → S3
- Labral tear, non-op → S4
- Post-op labral repair → S5
- Shoulder replacement → S6

### LOWER EXTREMITY ANALYSIS:
- Hip labral tear, non-op → H1
- Post-op hip arthroscopy → H2
- Meniscus tear, non-op → K1
- Post-op knee arthroscopy → K2
- ACL tear, non-op → K3
- Post-op ACL reconstruction → K4

## Key Rules:
1. ONLY select scenarios for STRUCTURAL injuries (herniations, tears, fractures, stenosis)
2. Sprains/strains do NOT get scenarios - they heal in 6-12 weeks
3. Multiple scenarios can apply to the same patient (e.g., C1 + C4 for disc + facet)
4. ONE-TIME vs RECURRING is determined by treatment history (see decision trees above)
5. Provide patient-specific rationales referencing actual findings and dates from records

## Output Format:
Return a JSON object with this structure:
{{
    "scenarios": ["C1", "C4"],
    "diagnoses": [
        {{"body_part": "Cervical Spine", "diagnosis": "C5-6 disc herniation", "structural": true, "date_documented": "7/10/2025"}},
        {{"body_part": "Cervical Spine", "diagnosis": "Facet syndrome", "structural": true, "date_documented": "7/10/2025"}}
    ],
    "rationales": {{
        "C1": "Surveillance of C5-6 disc herniation per 7/10/25 MRI showing moderate foraminal stenosis.",
        "C4": "One-time RFA for cervical facet syndrome with documented benefit from 8/15/25 MBB (80% relief), no prior RFA."
    }},
    "summary": "52-year-old with cervical disc herniation and facet syndrome. MBB provided significant relief. Recommend disc surveillance and one-time RFA."
}}

CRITICAL:
- Scenarios must be from the available list above
- Each rationale MUST reference specific findings and dates from the records
- Be conservative - typical cases have 2-5 scenarios, NOT 10+
"""

    user_prompt = f"""## Patient Information
- Name: {patient_info.get('patient_name', 'Unknown')}
- Date of Birth: {patient_info.get('date_of_birth', 'Unknown')}
- Date of Injury: {patient_info.get('date_of_injury', 'Unknown')}
- Life Expectancy: {patient_info.get('life_expectancy', 'Unknown')} years
- Age at Report: {patient_info.get('age_initiated', 'Unknown')}

## Medical Records Summary
{medical_summary}

Please analyze the medical records above and:
1. Identify all structural injuries by body region
2. Apply the decision trees to determine which scenarios apply
3. Provide patient-specific rationales for each scenario
4. Return your analysis as a JSON object

Remember: Only include scenarios for STRUCTURAL injuries. Sprains/strains get NO scenarios."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            system=system_prompt
        )

        # Extract the response text
        response_text = response.content[0].text

        # Try to parse JSON from the response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        result = json.loads(response_text)

        # Validate and normalize the response
        return {
            "scenarios": result.get("scenarios", []),
            "diagnoses": result.get("diagnoses", []),
            "rationales": result.get("rationales", {}),
            "summary": result.get("summary", ""),
            "error": None
        }

    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse Claude response: {str(e)}",
            "raw_response": response_text if 'response_text' in locals() else "No response",
            "scenarios": [],
            "diagnoses": [],
            "rationales": {},
            "summary": "Analysis failed - please try again"
        }
    except Exception as e:
        return {
            "error": f"Claude API error: {str(e)}",
            "scenarios": [],
            "diagnoses": [],
            "rationales": {},
            "summary": "Analysis failed - please try again"
        }


def extract_text_from_docx(file_path: str) -> str:
    """Extract text content from a Word document."""
    from docx import Document

    doc = Document(file_path)
    text_content = []

    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_content.append(paragraph.text)

    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_text:
                text_content.append(" | ".join(row_text))

    return "\n\n".join(text_content)
