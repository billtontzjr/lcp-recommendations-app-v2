"""
Scenario Master Parser - Parses the Orthopedic & Spine Scenario Master System document.

This parser extracts:
1. Global principles/rules
2. Scenario definitions with clinical patterns and key triggers
3. Default recommendations for each scenario

The parsed data is stored in Supabase for use during LCP generation.
"""

import re
import os
from typing import List, Dict, Tuple, Optional
from app.services.supabase_client import get_supabase_client


# Body region mapping from section headers
BODY_REGION_MAP = {
    'CERVICAL SPINE': 'cervical',
    'THORACIC SPINE': 'thoracic',
    'LUMBAR SPINE': 'lumbar',
    'SHOULDER': 'shoulder',
    'ELBOW': 'elbow',
    'WRIST AND HAND': 'wrist_hand',
    'HIP': 'hip',
    'KNEE': 'knee',
    'FOOT AND ANKLE': 'ankle_foot',
}

# Frequency parsing patterns
FREQUENCY_PATTERNS = {
    r'annually|annual|yearly|every year': 'yearly',
    r'every other year|every two years|every 2 years': 'every_2_years',
    r'every three years|every 3 years': 'every_3_years',
    r'every four years|every 4 years': 'every_4_years',
    r'every five years|every 5 years': 'every_5_years',
    r'every two to three years|every 2-3 years|every two to five years': 'every_3_years',
    r'every three to five years|every 3-5 years': 'every_4_years',
    r'one-time|one time|once': 'one_time',
    r'up to three.*per year|up to 3.*per year': '3x_year',
    r'up to two.*per year|up to 2.*per year': '2x_year',
}


def parse_frequency(text: str) -> Tuple[str, str]:
    """
    Parse frequency from recommendation text.

    Returns (internal_frequency, display_frequency)
    """
    text_lower = text.lower()

    for pattern, freq_code in FREQUENCY_PATTERNS.items():
        if re.search(pattern, text_lower):
            # Extract the display text
            match = re.search(pattern, text_lower)
            if match:
                return freq_code, text

    # Default to yearly if not matched
    return 'yearly', text


def extract_global_rules(content: str) -> List[Dict]:
    """Extract global principles from the document."""
    rules = []

    # Find the GLOBAL PRINCIPLES section
    global_section = re.search(
        r'### \*\*GLOBAL PRINCIPLES\*\*\s*(.*?)(?=\n---|\n## )',
        content,
        re.DOTALL | re.IGNORECASE
    )

    if not global_section:
        return rules

    section_text = global_section.group(1)

    # Parse numbered rules
    rule_pattern = r'(\d+)\.\s+\*\*([^*]+)\*\*\s*([^0-9]+?)(?=\d+\.\s+\*\*|\Z)'
    matches = re.findall(rule_pattern, section_text, re.DOTALL)

    for match in matches:
        rule_num = int(match[0])
        rule_title = match[1].strip()
        rule_text = match[2].strip()

        # Determine rule type
        rule_type = 'general'
        if 'sprain' in rule_text.lower() or 'strain' in rule_text.lower():
            rule_type = 'sprain_strain'
        elif 'surveillance' in rule_text.lower():
            rule_type = 'surveillance'
        elif 'esi' in rule_text.lower() or 'epidural' in rule_text.lower():
            rule_type = 'esi'
        elif 'rfa' in rule_text.lower() or 'radiofrequency' in rule_text.lower():
            rule_type = 'rfa'

        rules.append({
            'rule_number': rule_num,
            'rule_text': f"{rule_title}: {rule_text}",
            'rule_type': rule_type,
            'is_active': True
        })

    return rules


def extract_scenarios(content: str) -> List[Dict]:
    """Extract scenario definitions from the document."""
    scenarios = []
    current_body_region = None

    # Find all scenario blocks
    scenario_pattern = r'\*\*Scenario ([A-Z]\d+)\s*[—–-]\s*([^*]+)\*\*\s*(.*?)(?=\*\*Scenario [A-Z]\d+|### \*\*[A-Z]|## \*\*[IVX]+|---|\Z)'

    # First, identify body regions from section headers
    section_pattern = r'### \*\*([A-Z])\.\s+([A-Z\s/]+)SCENARIOS?\*\*'
    sections = re.findall(section_pattern, content)

    # Build a map of content positions to body regions
    region_positions = []
    for section_letter, section_name in sections:
        section_name = section_name.strip()
        for region_key, region_value in BODY_REGION_MAP.items():
            if region_key in section_name.upper():
                pos = content.find(f'### **{section_letter}. {section_name}')
                if pos == -1:
                    # Try alternate format
                    pos = content.find(f'{section_name}SCENARIOS')
                region_positions.append((pos, region_value))
                break

    region_positions.sort()

    def get_body_region(position: int) -> str:
        """Get body region for a position in the document."""
        region = 'unknown'
        for pos, reg in region_positions:
            if position >= pos:
                region = reg
        return region

    # Extract scenarios
    for match in re.finditer(scenario_pattern, content, re.DOTALL):
        scenario_code = match.group(1)
        scenario_name = match.group(2).strip()
        scenario_content = match.group(3)
        position = match.start()

        body_region = get_body_region(position)

        # Extract clinical pattern
        clinical_pattern = ""
        pattern_match = re.search(
            r'\*\s*\*\*Clinical pattern:\*\*\s*([^*]+?)(?=\*\s*\*\*Key record|$)',
            scenario_content,
            re.DOTALL
        )
        if pattern_match:
            clinical_pattern = pattern_match.group(1).strip()

        # Extract key record triggers
        key_triggers = ""
        triggers_match = re.search(
            r'\*\s*\*\*Key record triggers:\*\*\s*([^*]+?)(?=\*\s*\*\*Default|$)',
            scenario_content,
            re.DOTALL
        )
        if triggers_match:
            key_triggers = triggers_match.group(1).strip()

        # Determine if structural (requires surveillance)
        is_structural = 'structural' in clinical_pattern.lower() or \
                       'herniat' in clinical_pattern.lower() or \
                       'tear' in clinical_pattern.lower() or \
                       'fracture' in clinical_pattern.lower() or \
                       'stenosis' in clinical_pattern.lower()

        # Check if post-operative
        is_post_op = 'post-op' in scenario_name.lower() or \
                    'post op' in scenario_name.lower() or \
                    'surgery' in scenario_name.lower() or \
                    'fusion' in scenario_name.lower() or \
                    'arthroplasty' in scenario_name.lower() or \
                    'repair' in scenario_name.lower() or \
                    'orif' in scenario_name.lower()

        # Check if requires CT surveillance (fusions)
        requires_ct = 'fusion' in scenario_name.lower() or \
                     'fusion' in clinical_pattern.lower()

        scenarios.append({
            'scenario_code': scenario_code,
            'scenario_name': scenario_name,
            'body_region': body_region,
            'clinical_pattern': clinical_pattern,
            'key_record_triggers': key_triggers,
            'is_structural': is_structural,
            'is_post_operative': is_post_op,
            'requires_ct_surveillance': requires_ct,
            'is_active': True,
            'raw_content': scenario_content  # Keep for recommendation extraction
        })

    return scenarios


def extract_recommendations(scenario: Dict) -> List[Dict]:
    """Extract recommendations from a scenario's content."""
    recommendations = []
    content = scenario.get('raw_content', '')
    scenario_code = scenario['scenario_code']

    # Find the Default future recommendations section
    rec_match = re.search(
        r'\*\s*\*\*Default future recommendations:\*\*\s*(.*?)(?=\*\*Scenario|\Z)',
        content,
        re.DOTALL
    )

    if not rec_match:
        return recommendations

    rec_text = rec_match.group(1)

    # Parse numbered recommendations
    rec_pattern = r'(\d+)\.\s+([^\d]+?)(?=\d+\.\s+|\Z)'
    matches = re.findall(rec_pattern, rec_text, re.DOTALL)

    for i, match in enumerate(matches):
        rec_num = int(match[0])
        rec_text = match[1].strip()

        # Clean up the text
        rec_text = re.sub(r'\s+', ' ', rec_text)
        rec_text = re.sub(r'\[\d+\]', '', rec_text)  # Remove reference numbers
        rec_text = re.sub(r'\[User instruction\]', '', rec_text)

        # Determine category
        category = determine_category(rec_text)

        # Extract item name and frequency
        item_name, frequency, frequency_display, units, is_one_time = parse_recommendation(rec_text)

        # Determine fee type based on category
        fee_type = 'APC' if category in ['Procedures/Hospitalizations/Surgery', 'Diagnostic Testing/Assessment'] else 'PFR'

        recommendations.append({
            'scenario_code': scenario_code,
            'item_category': category,
            'item_name': item_name,
            'item_description': rec_text,
            'frequency': frequency,
            'frequency_display': frequency_display,
            'units': units,
            'fee_type': fee_type,
            'is_one_time': is_one_time,
            'is_active': True,
            'display_order': rec_num
        })

    return recommendations


def determine_category(text: str) -> str:
    """Determine the LCP category for a recommendation."""
    text_lower = text.lower()

    if any(term in text_lower for term in ['follow-up', 'visit', 'specialist', 'surgeon']):
        return 'Physician/Nurse Evaluations'
    elif any(term in text_lower for term in ['mri', 'ct scan', 'x-ray', 'radiograph', 'imaging', 'emg', 'ncv']):
        return 'Diagnostic Testing/Assessment'
    elif any(term in text_lower for term in ['physical therapy', 'occupational therapy', 'therapy']):
        return 'Therapies'
    elif any(term in text_lower for term in ['injection', 'esi', 'rfa', 'ablation', 'block', 'surgery', 'fusion', 'repair', 'arthroplasty', 'revision']):
        return 'Procedures/Hospitalizations/Surgery'
    elif any(term in text_lower for term in ['brace', 'splint', 'orthotic', 'cane', 'walker', 'wheelchair', 'shoe']):
        return 'Durable Medical Equipment'
    elif any(term in text_lower for term in ['medication', 'prescription']):
        return 'Medications'
    else:
        return 'Other Services'


def parse_recommendation(text: str) -> Tuple[str, str, str, int, bool]:
    """
    Parse a recommendation to extract item name, frequency, units, and one-time flag.

    Returns: (item_name, frequency, frequency_display, units, is_one_time)
    """
    # Default values
    frequency = 'yearly'
    frequency_display = 'Annually'
    units = 1
    is_one_time = False

    text_lower = text.lower()

    # Check for one-time
    if 'one-time' in text_lower or 'one time' in text_lower:
        is_one_time = True
        frequency = 'one_time'
        frequency_display = 'One Time'

    # Check for frequency patterns
    if 'annually' in text_lower or 'annual' in text_lower or 'every year' in text_lower:
        frequency = 'yearly'
        frequency_display = 'Annually'
    elif 'every other year' in text_lower or 'every two years' in text_lower or 'every 2 years' in text_lower:
        frequency = 'every_2_years'
        frequency_display = 'Every 2 Years'
    elif 'every three years' in text_lower or 'every 3 years' in text_lower:
        frequency = 'every_3_years'
        frequency_display = 'Every 3 Years'
    elif 'every five years' in text_lower or 'every 5 years' in text_lower:
        frequency = 'every_5_years'
        frequency_display = 'Every 5 Years'
    elif 'every two to three years' in text_lower or 'every 2-3 years' in text_lower:
        frequency = 'every_3_years'
        frequency_display = 'Every 2-3 Years'
    elif 'every three to five years' in text_lower or 'every 3-5 years' in text_lower:
        frequency = 'every_4_years'
        frequency_display = 'Every 3-5 Years'
    elif 'up to three' in text_lower:
        frequency = '3x_year'
        frequency_display = 'Up to 3 Per Year'
    elif 'up to two' in text_lower:
        frequency = '2x_year'
        frequency_display = 'Up to 2 Per Year'

    # Extract units (e.g., "24 visits", "12-24 visits")
    units_match = re.search(r'(\d+)(?:-(\d+))?\s*visits?', text_lower)
    if units_match:
        if units_match.group(2):
            # Range like "12-24 visits" - use the higher number
            units = int(units_match.group(2))
        else:
            units = int(units_match.group(1))

    # Extract item name (first part before colon or period)
    item_name = text.split(':')[0].strip()
    item_name = re.sub(r'^\d+\.\s*', '', item_name)
    item_name = re.sub(r'\*+', '', item_name)

    # Clean up common patterns
    if len(item_name) > 100:
        # Try to get a shorter name
        if 'specialist follow-up' in text_lower:
            if 'spine' in text_lower:
                item_name = 'Spine Specialist Follow-up'
            elif 'orthopedic' in text_lower:
                item_name = 'Orthopedic Specialist Follow-up'
            else:
                item_name = 'Specialist Follow-up'
        elif 'physical therapy' in text_lower:
            item_name = 'Physical Therapy'
        elif 'mri' in text_lower:
            item_name = 'MRI'
        elif 'radiograph' in text_lower or 'x-ray' in text_lower:
            item_name = 'X-rays'

    return item_name, frequency, frequency_display, units, is_one_time


def parse_and_store_scenario_master(content: str, document_name: str) -> Dict:
    """
    Parse the Scenario Master document and store in Supabase.

    Args:
        content: The markdown content of the document
        document_name: Name of the uploaded document

    Returns:
        Dict with parsing results
    """
    supabase = get_supabase_client()
    if not supabase:
        return {'error': 'Supabase not configured', 'success': False}

    results = {
        'rules_parsed': 0,
        'scenarios_parsed': 0,
        'recommendations_parsed': 0,
        'success': True,
        'errors': []
    }

    try:
        # 1. Parse global rules
        rules = extract_global_rules(content)
        results['rules_parsed'] = len(rules)

        # Clear existing rules and insert new ones
        supabase.table('scenario_global_rules').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        if rules:
            supabase.table('scenario_global_rules').insert(rules).execute()

        # 2. Parse scenarios
        scenarios = extract_scenarios(content)
        results['scenarios_parsed'] = len(scenarios)

        # Clear existing scenarios
        supabase.table('scenario_recommendations').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        supabase.table('scenario_definitions').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

        # Insert scenarios and their recommendations
        for scenario in scenarios:
            raw_content = scenario.pop('raw_content', '')

            # Insert scenario definition
            supabase.table('scenario_definitions').insert(scenario).execute()

            # Extract and insert recommendations
            scenario['raw_content'] = raw_content
            recommendations = extract_recommendations(scenario)
            results['recommendations_parsed'] += len(recommendations)

            if recommendations:
                supabase.table('scenario_recommendations').insert(recommendations).execute()

        # 3. Store the document version
        version_record = {
            'document_name': document_name,
            'version_date': '2025-12-01',  # Extract from document name if possible
            'raw_content': content,
            'scenario_count': results['scenarios_parsed'],
            'rule_count': results['rules_parsed'],
            'is_active': True
        }
        supabase.table('scenario_master_versions').insert(version_record).execute()

    except Exception as e:
        results['success'] = False
        results['errors'].append(str(e))

    return results


def get_scenario_by_code(scenario_code: str) -> Optional[Dict]:
    """Get a scenario definition by its code."""
    supabase = get_supabase_client()
    if not supabase:
        return None

    try:
        result = supabase.table('scenario_definitions').select('*').eq('scenario_code', scenario_code).single().execute()
        return result.data
    except:
        return None


def get_scenarios_by_region(body_region: str) -> List[Dict]:
    """Get all scenarios for a body region."""
    supabase = get_supabase_client()
    if not supabase:
        return []

    try:
        result = supabase.table('scenario_definitions').select('*').eq('body_region', body_region).eq('is_active', True).execute()
        return result.data or []
    except:
        return []


def get_scenario_recommendations(scenario_code: str) -> List[Dict]:
    """Get all recommendations for a scenario."""
    supabase = get_supabase_client()
    if not supabase:
        return []

    try:
        result = supabase.table('scenario_recommendations').select('*').eq('scenario_code', scenario_code).eq('is_active', True).order('display_order').execute()
        return result.data or []
    except:
        return []


def get_all_scenarios() -> List[Dict]:
    """Get all active scenario definitions."""
    supabase = get_supabase_client()
    if not supabase:
        return []

    try:
        result = supabase.table('scenario_definitions').select('*').eq('is_active', True).order('scenario_code').execute()
        return result.data or []
    except:
        return []


def get_global_rules() -> List[Dict]:
    """Get all active global rules."""
    supabase = get_supabase_client()
    if not supabase:
        return []

    try:
        result = supabase.table('scenario_global_rules').select('*').eq('is_active', True).order('rule_number').execute()
        return result.data or []
    except:
        return []
