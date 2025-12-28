"""
Scenario Mapper - Phase 2 of LCP Generation.

Takes selected scenarios and deterministically maps them to items with costs.
This is the non-AI phase - purely lookup and calculation.
"""

from app.services.scenario_bundles import SCENARIO_BUNDLES, get_scenario


# Frequency multipliers for annual cost calculation
FREQUENCY_MULTIPLIERS = {
    "yearly": 1.0,
    "2x_year": 2.0,
    "3x_year": 3.0,
    "every_2_years": 0.5,
    "every_3_years": 0.333,
    "every_4_years": 0.25,
    "every_5_years": 0.2,
    "one_time": 0.0,  # One-time costs have $0 annual
}


def lookup_pfr_price(cpt_code: str, pfr_lookup: dict) -> float:
    """Look up professional fee from PFR sheet."""
    if isinstance(cpt_code, list):
        # Sum up prices for multiple codes (e.g., RFA with add-ons)
        total = 0.0
        for code in cpt_code:
            total += pfr_lookup.get(str(code).strip(), 0.0)
        return total
    return pfr_lookup.get(str(cpt_code).strip(), 0.0)


def lookup_apc_price(cpt_code: str, apc_lookup: dict, geo_multiplier: float) -> float:
    """Look up facility fee from APC sheet with geographic multiplier."""
    if isinstance(cpt_code, list):
        # For facility fees, usually just the primary code
        cpt_code = cpt_code[0]
    base_rate = apc_lookup.get(str(cpt_code).strip(), 0.0)
    return base_rate * geo_multiplier


def calculate_item_cost(item: dict, pfr_lookup: dict, apc_lookup: dict, geo_multiplier: float) -> dict:
    """
    Calculate costs for a single item.

    Returns dict with unit_cost, annual_cost, one_time_cost
    """
    cpt = item.get("cpt", "")
    fee_type = item.get("fee_type", "PFR")
    frequency = item.get("frequency", "yearly")
    units = item.get("units", 1)
    item_type = item.get("type", "recurring")

    # Get base unit cost
    if fee_type == "PFR":
        unit_cost = lookup_pfr_price(cpt, pfr_lookup)
    elif fee_type == "APC":
        unit_cost = lookup_apc_price(cpt, apc_lookup, geo_multiplier)
    else:
        unit_cost = 0.0

    # Apply units multiplier (e.g., 24 PT visits)
    total_unit_cost = unit_cost * units

    # Calculate annual and one-time costs based on type and frequency
    if item_type == "one_time":
        return {
            "unit_cost": round(total_unit_cost, 2),
            "annual_cost": 0.0,
            "one_time_cost": round(total_unit_cost, 2)
        }
    else:  # recurring
        multiplier = FREQUENCY_MULTIPLIERS.get(frequency, 1.0)
        annual_cost = total_unit_cost * multiplier
        return {
            "unit_cost": round(total_unit_cost, 2),
            "annual_cost": round(annual_cost, 2),
            "one_time_cost": 0.0
        }


def expand_scenarios_to_items(
    scenario_codes: list,
    pfr_lookup: dict,
    apc_lookup: dict,
    patient_info: dict,
    rationales: dict = None
) -> list:
    """
    Expand scenario codes into a consolidated item list with costs.

    Args:
        scenario_codes: List of scenario codes (e.g., ["C1", "C4"])
        pfr_lookup: CPT -> price lookup from PFR sheet
        apc_lookup: CPT -> price lookup from APC sheet
        patient_info: Patient info including geographic_multiplier
        rationales: Optional dict mapping scenario code to rationale text

    Returns:
        List of items with all costs calculated, ready for document generation
    """
    geo_multiplier = float(patient_info.get("geographic_multiplier", 1.0) or 1.0)
    rationales = rationales or {}

    # Track items to deduplicate (key = category + description)
    seen_items = {}
    all_items = []

    for code in scenario_codes:
        scenario = get_scenario(code)
        if not scenario:
            continue

        # Use Claude's patient-specific rationale (no mention of internal scenario system)
        scenario_rationale = rationales.get(code, "")

        for item_def in scenario.get("items", []):
            # Create unique key for deduplication
            item_key = f"{item_def['category']}|{item_def['description']}"

            # Skip duplicates (e.g., spine specialist visits from multiple scenarios)
            if item_key in seen_items:
                # Keep the existing rationale (first scenario's rationale wins)
                continue

            # Calculate costs
            costs = calculate_item_cost(item_def, pfr_lookup, apc_lookup, geo_multiplier)

            # Build the full item record
            item = {
                "category": item_def["category"],
                "item": item_def["description"],
                "subcategory": "",
                "service_description": item_def["description"],
                "code_type": item_def.get("fee_type", "PFR"),
                "code": item_def["cpt"] if isinstance(item_def["cpt"], str) else "; ".join(item_def["cpt"]),
                "cost": costs["unit_cost"],
                "frequency": format_frequency_display(item_def["frequency"]),
                "source": "Medical Records",
                "rationale": scenario_rationale,
                "unit_cost": costs["unit_cost"],
                "annual_cost": costs["annual_cost"],
                "one_time_cost": costs["one_time_cost"],
                "scenario_code": code,
            }

            seen_items[item_key] = item
            all_items.append(item)

    return all_items


def format_frequency_display(frequency: str) -> str:
    """Convert internal frequency code to display format."""
    display_map = {
        "yearly": "Yearly",
        "2x_year": "2 Times Per Year",
        "3x_year": "3 Times Per Year",
        "every_2_years": "Every 2 Years",
        "every_3_years": "Every 3 Years",
        "every_4_years": "Every 4 Years",
        "every_5_years": "Every 5 Years",
        "one_time": "One Time",
    }
    return display_map.get(frequency, frequency.replace("_", " ").title())


def calculate_totals(items: list, patient_info: dict) -> dict:
    """
    Calculate category totals and grand totals from items list.

    Returns the same structure as cost_calculator.calculate_all_costs()
    """
    life_expectancy = float(patient_info.get("life_expectancy", 0) or 0)

    category_totals = {}

    for item in items:
        category = item.get("category", "Uncategorized")

        if category not in category_totals:
            category_totals[category] = {
                "annual_cost": 0.0,
                "one_time_cost": 0.0,
                "items": []
            }

        category_totals[category]["annual_cost"] += item.get("annual_cost", 0.0)
        category_totals[category]["one_time_cost"] += item.get("one_time_cost", 0.0)
        category_totals[category]["items"].append(item)

    # Calculate grand totals
    total_annual = sum(ct["annual_cost"] for ct in category_totals.values())
    total_one_time = sum(ct["one_time_cost"] for ct in category_totals.values())
    lifetime_annual = total_annual * life_expectancy
    grand_total = lifetime_annual + total_one_time

    return {
        "items": items,
        "category_totals": category_totals,
        "totals": {
            "total_annual": round(total_annual, 2),
            "total_one_time": round(total_one_time, 2),
            "lifetime_annual": round(lifetime_annual, 2),
            "grand_total": round(grand_total, 2),
            "life_expectancy": life_expectancy,
        }
    }


def parse_provider_frequency(frequency_str: str) -> tuple:
    """
    Parse provider-stated frequency into internal format and display format.

    Returns (internal_frequency, display_frequency)
    """
    freq_lower = frequency_str.lower().strip()

    # Common frequency mappings
    if "every 2 year" in freq_lower or "every two year" in freq_lower or "biennial" in freq_lower:
        return "every_2_years", "Every 2 Years"
    elif "every 3 year" in freq_lower or "every three year" in freq_lower:
        return "every_3_years", "Every 3 Years"
    elif "every 4 year" in freq_lower or "every four year" in freq_lower:
        return "every_4_years", "Every 4 Years"
    elif "every 5 year" in freq_lower or "every five year" in freq_lower:
        return "every_5_years", "Every 5 Years"
    elif "twice" in freq_lower or "2x" in freq_lower or "two times" in freq_lower:
        return "2x_year", "2 Times Per Year"
    elif "three times" in freq_lower or "3x" in freq_lower:
        return "3x_year", "3 Times Per Year"
    elif "annual" in freq_lower or "yearly" in freq_lower or "per year" in freq_lower or "each year" in freq_lower:
        return "yearly", "Yearly"
    elif "one time" in freq_lower or "once" in freq_lower or "one-time" in freq_lower:
        return "one_time", "One Time"
    else:
        # Use original as display, default to yearly for calculation
        return "yearly", frequency_str


def expand_provider_items(
    provider_items: list,
    pfr_lookup: dict,
    apc_lookup: dict,
    patient_info: dict,
    seen_items: dict
) -> tuple:
    """
    Expand provider-recommended items into the standard item format.

    These are items directly recommended by treating providers with their
    own frequencies and rationales citing the provider.

    Returns:
        Tuple of (items_list, suggested_rows_list)
        - items_list: Items that can be costed (found in workbook or estimated)
        - suggested_rows_list: Items with CPT codes not found in workbook (suggested new rows)
    """
    geo_multiplier = float(patient_info.get("geographic_multiplier", 1.0) or 1.0)
    items = []
    suggested_rows = []

    for provider_item in provider_items:
        item_name = provider_item.get("item", "")
        frequency_str = provider_item.get("frequency", "Yearly")
        provider_name = provider_item.get("provider_name", "Treating Provider")
        rationale = provider_item.get("rationale", "")
        body_part = provider_item.get("body_part", "")
        suggested_cpt = provider_item.get("suggested_cpt", "")
        suggested_category = provider_item.get("suggested_category", "")

        # Parse frequency
        internal_freq, display_freq = parse_provider_frequency(frequency_str)

        # Determine category - use Claude's suggestion or derive from body part
        category = suggested_category or "Diagnostic Testing/Assessment"
        if not suggested_category and body_part:
            # Default categorization based on body part
            pass  # Keep default category

        # Create unique key for deduplication
        item_key = f"{category}|{item_name}"
        if item_key in seen_items:
            continue

        # Try to look up the suggested CPT code in the workbook
        unit_cost = 0.0
        found_in_workbook = False
        code_type = "PFR"

        if suggested_cpt:
            # First try PFR lookup
            pfr_price = pfr_lookup.get(str(suggested_cpt).strip(), 0.0)
            if pfr_price > 0:
                unit_cost = pfr_price
                found_in_workbook = True
                code_type = "PFR"
            else:
                # Try APC lookup
                apc_price = apc_lookup.get(str(suggested_cpt).strip(), 0.0)
                if apc_price > 0:
                    unit_cost = apc_price * geo_multiplier
                    found_in_workbook = True
                    code_type = "APC"

        # If CPT not found in workbook, this is a suggested new row
        if suggested_cpt and not found_in_workbook:
            suggested_row = {
                "item": item_name,
                "suggested_cpt": suggested_cpt,
                "suggested_category": category,
                "frequency": display_freq,
                "provider_name": provider_name,
                "body_part": body_part,
                "rationale": rationale,
                "message": f"CPT {suggested_cpt} not found in workbook. Consider adding this row to your Master Workbook."
            }
            suggested_rows.append(suggested_row)

            # Still create the item with an estimated cost
            unit_cost = 500.0  # Default estimate

        elif not suggested_cpt:
            # No CPT suggested, use default estimate
            unit_cost = 500.0

        # Determine if one-time or recurring
        is_one_time = internal_freq == "one_time"

        if is_one_time:
            annual_cost = 0.0
            one_time_cost = unit_cost
        else:
            multiplier = FREQUENCY_MULTIPLIERS.get(internal_freq, 1.0)
            annual_cost = unit_cost * multiplier
            one_time_cost = 0.0

        item = {
            "category": category,
            "item": item_name,
            "subcategory": body_part,
            "service_description": item_name,
            "code_type": code_type if found_in_workbook else "Provider Recommendation",
            "code": suggested_cpt if suggested_cpt else "N/A",
            "cost": round(unit_cost, 2),
            "frequency": display_freq,
            "source": f"Treating Provider: {provider_name}",
            "rationale": rationale,
            "unit_cost": round(unit_cost, 2),
            "annual_cost": round(annual_cost, 2),
            "one_time_cost": round(one_time_cost, 2),
            "scenario_code": "PROVIDER",
            "provider_name": provider_name,
            "found_in_workbook": found_in_workbook,
            "suggested_cpt": suggested_cpt,
        }

        seen_items[item_key] = item
        items.append(item)

    return items, suggested_rows


def scenarios_to_cost_data(
    scenario_codes: list,
    workbook_data: dict,
    rationales: dict = None,
    provider_items: list = None
) -> dict:
    """
    Main entry point: Convert scenarios to full cost data structure.

    Args:
        scenario_codes: List of scenario codes from Claude analysis
        workbook_data: Parsed workbook with patient_info, pfr_lookup, apc_lookup
        rationales: Optional scenario-specific rationales from Claude
        provider_items: Optional list of provider-recommended items from Claude

    Returns:
        Cost data structure ready for document generation, including:
        - items: All costed items
        - suggested_rows: Items with CPT codes not found in workbook
    """
    pfr_lookup = workbook_data.get("pfr_lookup", {})
    apc_lookup = workbook_data.get("apc_lookup", {})
    patient_info = workbook_data.get("patient_info", {})

    # Track seen items to avoid duplicates
    seen_items = {}
    suggested_rows = []

    # First expand scenario-based items
    items = expand_scenarios_to_items(
        scenario_codes,
        pfr_lookup,
        apc_lookup,
        patient_info,
        rationales
    )

    # Track seen items from scenarios
    for item in items:
        item_key = f"{item['category']}|{item['item']}"
        seen_items[item_key] = item

    # Then add provider-recommended items (avoiding duplicates)
    if provider_items:
        provider_expanded, provider_suggested = expand_provider_items(
            provider_items,
            pfr_lookup,
            apc_lookup,
            patient_info,
            seen_items
        )
        items.extend(provider_expanded)
        suggested_rows.extend(provider_suggested)

    result = calculate_totals(items, patient_info)
    result["suggested_rows"] = suggested_rows

    return result
