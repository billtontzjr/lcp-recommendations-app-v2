"""Claude API service for medical record analysis and item selection."""
import os
import json
from anthropic import Anthropic
from app.config import Config

# Load reference files
REFERENCES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'references')


def load_reference_file(filename):
    """Load a reference file from the references directory."""
    filepath = os.path.join(REFERENCES_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return f.read()
    return ""


def get_clinical_scenarios():
    """Load clinical scenarios reference."""
    return load_reference_file('clinical_scenarios.md')


def get_global_principles():
    """Load global principles reference."""
    return load_reference_file('global_principles.md')


def analyze_medical_records(medical_summary: str, patient_info: dict, available_items: list) -> dict:
    """
    Use Claude to analyze medical records and select appropriate care items.

    Args:
        medical_summary: Text content from the medical records document
        patient_info: Dict with patient name, DOB, life expectancy, etc.
        available_items: List of all available items from the Master sheet

    Returns:
        Dict with:
        - diagnoses: List of identified diagnoses
        - scenarios: List of matched clinical scenarios
        - selected_items: List of items to include with rationales
    """
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    clinical_scenarios = get_clinical_scenarios()
    global_principles = get_global_principles()

    # Format available items for the prompt
    items_list = "\n".join([
        f"- Category: {item.get('category', '')} | Item: {item.get('item', '')} | "
        f"Subcategory: {item.get('subcategory', '')} | Code: {item.get('code', '')} | "
        f"Frequency: {item.get('frequency', '')}"
        for item in available_items
    ])

    system_prompt = f"""You are a medical expert assistant helping Dr. William Tontz, MD, CLCP create Life Care Plan recommendations.

Your task is to analyze medical records and select appropriate care items based on documented injuries and treatments.

## Clinical Scenarios Reference
{clinical_scenarios}

## Global Principles
{global_principles}

## Key Rules:
1. ONLY include items for documented structural injuries (disc herniations, tears, fractures)
2. Sprains/strains do NOT require long-term surveillance
3. Only include treatments the patient has tried AND documented benefit from
4. Follow the Structural Injury Surveillance Rule for spine injuries
5. Be conservative - typically 10-25 items, NOT 75+
6. Each item needs a patient-specific rationale referencing actual findings and dates from the records

## Output Format:
Return a JSON object with this structure:
{{
    "diagnoses": [
        {{"body_part": "Lumbar Spine", "diagnosis": "L4-5, L5-S1 disc herniations", "structural": true, "date_documented": "7/10/2025"}}
    ],
    "matched_scenarios": ["L1", "L8"],
    "selected_items": [
        {{
            "category": "Physicians",
            "item": "Spine Specialist Follow-up",
            "frequency": "1x/year",
            "rationale": "Annual surveillance of L4-5, L5-S1 disc herniations per 7/10/25 MRI.",
            "source": "Medical Records"
        }}
    ],
    "summary": "Brief summary of injuries and care needs"
}}
"""

    user_prompt = f"""## Patient Information
- Name: {patient_info.get('patient_name', 'Unknown')}
- Date of Birth: {patient_info.get('date_of_birth', 'Unknown')}
- Date of Injury: {patient_info.get('date_of_injury', 'Unknown')}
- Life Expectancy: {patient_info.get('life_expectancy', 'Unknown')} years
- Age Initiated: {patient_info.get('age_initiated', 'Unknown')}

## Medical Records Summary
{medical_summary}

## Available Items from Master Workbook
{items_list}

Please analyze the medical records above and:
1. Identify all documented injuries/diagnoses
2. Classify each as structural vs non-structural
3. Match to the appropriate clinical scenarios
4. Select ONLY the relevant items from the available items list
5. Provide patient-specific rationales for each selected item

Return your analysis as a JSON object."""

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
        # Handle case where response might have markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        result = json.loads(response_text)
        return result

    except json.JSONDecodeError as e:
        # If JSON parsing fails, return a structured error
        return {
            "error": f"Failed to parse Claude response: {str(e)}",
            "raw_response": response_text if 'response_text' in locals() else "No response",
            "diagnoses": [],
            "matched_scenarios": [],
            "selected_items": [],
            "summary": "Analysis failed - please try again"
        }
    except Exception as e:
        return {
            "error": f"Claude API error: {str(e)}",
            "diagnoses": [],
            "matched_scenarios": [],
            "selected_items": [],
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

    return "\n\n".join(text_content)


def match_items_to_workbook(selected_items: list, workbook_items: list) -> list:
    """
    Match Claude's selected items to actual items in the workbook.

    Args:
        selected_items: Items selected by Claude with rationales
        workbook_items: All items from the Master sheet

    Returns:
        List of workbook items with 'selected' flag and rationales added
    """
    matched_items = []

    for selected in selected_items:
        selected_category = selected.get('category', '').lower()
        selected_item = selected.get('item', '').lower()

        # Find matching item in workbook
        for wb_item in workbook_items:
            wb_category = str(wb_item.get('category', '')).lower()
            wb_item_name = str(wb_item.get('item', '')).lower()

            # Check for match (fuzzy matching)
            if (selected_category in wb_category or wb_category in selected_category) and \
               (selected_item in wb_item_name or wb_item_name in selected_item):
                matched_item = wb_item.copy()
                matched_item['selected'] = True
                matched_item['rationale'] = selected.get('rationale', '')
                matched_item['source'] = selected.get('source', 'Medical Records')
                # Use Claude's frequency if provided
                if selected.get('frequency'):
                    matched_item['frequency'] = selected.get('frequency')
                matched_items.append(matched_item)
                break
        else:
            # If no exact match found, create a new item from Claude's selection
            matched_items.append({
                'category': selected.get('category', 'Uncategorized'),
                'item': selected.get('item', ''),
                'subcategory': selected.get('subcategory', ''),
                'service_description': selected.get('item', ''),
                'code_type': '',
                'code': '',
                'cost': 0,
                'frequency': selected.get('frequency', ''),
                'source': selected.get('source', 'Medical Records'),
                'rationale': selected.get('rationale', ''),
                'selected': True
            })

    return matched_items
