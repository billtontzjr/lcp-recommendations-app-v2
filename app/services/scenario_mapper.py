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

        scenario_name = scenario.get("name", code)
        scenario_rationale = rationales.get(code, f"Per {scenario_name} clinical scenario.")

        for item_def in scenario.get("items", []):
            # Create unique key for deduplication
            item_key = f"{item_def['category']}|{item_def['description']}"

            # Skip duplicates (e.g., spine specialist visits from multiple scenarios)
            if item_key in seen_items:
                # Update rationale to include both scenarios
                existing = seen_items[item_key]
                if scenario_name not in existing.get("rationale", ""):
                    existing["rationale"] += f" Also per {scenario_name}."
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


def scenarios_to_cost_data(
    scenario_codes: list,
    workbook_data: dict,
    rationales: dict = None
) -> dict:
    """
    Main entry point: Convert scenarios to full cost data structure.

    Args:
        scenario_codes: List of scenario codes from Claude analysis
        workbook_data: Parsed workbook with patient_info, pfr_lookup, apc_lookup
        rationales: Optional scenario-specific rationales from Claude

    Returns:
        Cost data structure ready for document generation
    """
    items = expand_scenarios_to_items(
        scenario_codes,
        workbook_data.get("pfr_lookup", {}),
        workbook_data.get("apc_lookup", {}),
        workbook_data.get("patient_info", {}),
        rationales
    )

    return calculate_totals(items, workbook_data.get("patient_info", {}))
