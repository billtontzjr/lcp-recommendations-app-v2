"""
Custom Clinical Rules Service.

Fetches Dr. Tontz's explicit clinical decision rules from Supabase
and formats them for inclusion in the Claude analysis prompt.

These rules are deterministic and explicit - no inference or guessing.
"""

import os
from typing import List, Dict, Optional

# Try to import Supabase, but allow fallback if not configured
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


def get_supabase_client() -> Optional['Client']:
    """Get Supabase client if configured."""
    if not SUPABASE_AVAILABLE:
        return None

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


def fetch_active_rules() -> List[Dict]:
    """
    Fetch all active clinical rules from Supabase.

    Returns list of rule dictionaries, sorted by priority (highest first).
    Falls back to default rules if Supabase is not configured.
    """
    client = get_supabase_client()

    if client:
        try:
            response = client.table('clinical_rules') \
                .select('*') \
                .eq('is_active', True) \
                .order('priority', desc=True) \
                .execute()

            if response.data:
                return response.data
        except Exception as e:
            print(f"Warning: Could not fetch rules from Supabase: {e}")

    # Fallback to default rules if Supabase not available
    return get_default_rules()


def get_default_rules() -> List[Dict]:
    """
    Default clinical rules when Supabase is not configured.
    These are Dr. Tontz's core principles.
    """
    return [
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
            "rule_name": "Structural injuries only",
            "condition_description": "Any body region being evaluated",
            "action_description": "Only include scenarios for STRUCTURAL injuries (herniations, tears, fractures, stenosis). Sprains and strains heal in 6-12 weeks and do NOT require long-term care or surveillance.",
            "priority": 300
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
            "category": "diagnosis",
            "rule_name": "Myelopathy is serious",
            "condition_description": "MRI or clinical findings indicate myelopathy",
            "action_description": "Myelopathy requires surgical evaluation. This is a progressive condition - always recommend surgical consultation if present.",
            "priority": 250
        },
        {
            "category": "age",
            "rule_name": "Elderly patient considerations",
            "condition_description": "Patient is 75 years or older",
            "action_description": "Be more conservative with elderly patients. Prefer non-surgical management unless surgery has already been performed. Consider reduced PT visit frequencies.",
            "priority": 150
        },
    ]


def format_rules_for_prompt(rules: List[Dict]) -> str:
    """
    Format rules as clear instructions for the Claude prompt.

    Returns a formatted string to include in the system prompt.
    """
    if not rules:
        return ""

    lines = [
        "## Dr. Tontz's Clinical Decision Rules",
        "",
        "Apply these explicit rules when analyzing the case. These are MANDATORY and override general guidelines:",
        ""
    ]

    # Group rules by category
    categories = {}
    for rule in rules:
        cat = rule.get('category', 'general')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(rule)

    category_titles = {
        'general': 'General Principles',
        'age': 'Age-Based Rules',
        'treatment_history': 'Treatment History Rules',
        'diagnosis': 'Diagnosis-Specific Rules',
        'body_part': 'Body Part Rules'
    }

    for cat, cat_rules in categories.items():
        title = category_titles.get(cat, cat.title())
        lines.append(f"### {title}")
        lines.append("")

        for rule in cat_rules:
            name = rule.get('rule_name', 'Rule')
            condition = rule.get('condition_description', '')
            action = rule.get('action_description', '')

            lines.append(f"**{name}**")
            lines.append(f"- WHEN: {condition}")
            lines.append(f"- THEN: {action}")
            lines.append("")

    return "\n".join(lines)


def get_rules_for_analysis() -> str:
    """
    Main entry point: Fetch rules and format for Claude prompt.

    Returns formatted rules string ready to include in the system prompt.
    """
    rules = fetch_active_rules()
    return format_rules_for_prompt(rules)


def add_rule(
    category: str,
    rule_name: str,
    condition_description: str,
    action_description: str,
    subcategory: str = None,
    priority: int = 100
) -> Optional[Dict]:
    """
    Add a new clinical rule to the database.

    Returns the created rule or None if failed.
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        response = client.table('clinical_rules').insert({
            'category': category,
            'subcategory': subcategory,
            'rule_name': rule_name,
            'condition_description': condition_description,
            'action_description': action_description,
            'priority': priority,
            'is_active': True
        }).execute()

        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error adding rule: {e}")
        return None


def update_rule(rule_id: str, updates: Dict) -> Optional[Dict]:
    """Update an existing rule."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        response = client.table('clinical_rules') \
            .update(updates) \
            .eq('id', rule_id) \
            .execute()

        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error updating rule: {e}")
        return None


def deactivate_rule(rule_id: str) -> bool:
    """Deactivate a rule (soft delete)."""
    result = update_rule(rule_id, {'is_active': False})
    return result is not None


def list_all_rules(include_inactive: bool = False) -> List[Dict]:
    """List all rules for admin interface."""
    client = get_supabase_client()

    if client:
        try:
            query = client.table('clinical_rules').select('*')

            if not include_inactive:
                query = query.eq('is_active', True)

            response = query.order('category').order('priority', desc=True).execute()
            return response.data or []
        except Exception:
            pass

    return get_default_rules()
