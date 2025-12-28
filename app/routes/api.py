"""API endpoints for LCP generation."""
import os
import uuid
import tempfile
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

from app.services.workbook_parser import (
    parse_workbook,
    parse_workbook_all_items,
    WorkbookParseError,
    NoItemsSelectedError,
    MissingPatientInfoError
)
from app.services.cost_calculator import calculate_all_costs
from app.services.document_generator import generate_lcp_document
from app.services.claude_analyzer import (
    analyze_medical_records,
    extract_text_from_docx
)
from app.services.scenario_mapper import scenarios_to_cost_data
from app.services.supabase_client import (
    save_case,
    save_case_items,
    save_document_metadata,
    upload_file_to_storage,
    get_cases,
    get_case,
    get_case_items,
    get_documents,
    get_download_url
)
from app.services.custom_rules import (
    list_all_rules,
    add_rule,
    update_rule,
    deactivate_rule
)

api_bp = Blueprint('api', __name__, url_prefix='/api')

ALLOWED_EXTENSIONS = {'xlsx', 'xlsm'}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.route('/generate', methods=['POST'])
def generate_lcp():
    """
    Generate LCP recommendations from uploaded workbook.

    Expects multipart/form-data with:
        - file: Master Workbook (.xlsm/.xlsx)
        - medical_summary: Optional medical summary (.docx)
        - provider_recommendations: Optional treating provider recommendations (.docx)

    If medical_summary or provider_recommendations is provided, uses Claude AI
    to analyze records and automatically select appropriate items based on
    clinical scenarios and provider recommendations.

    If no documents provided, uses pre-checked items from workbook.

    Returns:
        The generated Word document as a download
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload .xlsx or .xlsm file'}), 400

    # Save uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    filename = secure_filename(file.filename)
    workbook_path = os.path.join(temp_dir, filename)
    file.save(workbook_path)

    # Check for medical summary file (enables AI-powered selection)
    medical_summary_path = None
    if 'medical_summary' in request.files:
        summary_file = request.files['medical_summary']
        if summary_file.filename and summary_file.filename.endswith('.docx'):
            summary_filename = secure_filename(summary_file.filename)
            medical_summary_path = os.path.join(temp_dir, summary_filename)
            summary_file.save(medical_summary_path)

    # Check for provider recommendations file
    provider_recommendations_path = None
    if 'provider_recommendations' in request.files:
        provider_file = request.files['provider_recommendations']
        if provider_file.filename and provider_file.filename.endswith('.docx'):
            provider_filename = secure_filename(provider_file.filename)
            provider_recommendations_path = os.path.join(temp_dir, provider_filename)
            provider_file.save(provider_recommendations_path)

    try:
        if medical_summary_path or provider_recommendations_path:
            # AI-POWERED MODE: Use Claude to identify scenarios, then map to items
            current_app.logger.info("AI-powered mode: Analyzing medical records with Claude")

            # Parse workbook to get patient info and pricing lookups
            workbook_data = parse_workbook_all_items(workbook_path)

            # Extract text from medical summary (if provided)
            medical_text = ""
            if medical_summary_path:
                medical_text = extract_text_from_docx(medical_summary_path)

            # Extract text from provider recommendations (if provided)
            provider_text = ""
            if provider_recommendations_path:
                provider_text = extract_text_from_docx(provider_recommendations_path)
                current_app.logger.info("Provider recommendations document uploaded")

            # Phase 1: Use Claude to identify applicable scenarios
            analysis_result = analyze_medical_records(
                medical_text,
                workbook_data['patient_info'],
                provider_recommendations=provider_text
            )

            # Check for errors in Claude response
            if analysis_result.get('error'):
                current_app.logger.warning(f"Claude analysis warning: {analysis_result['error']}")

            # Get scenario codes and provider items from Claude's analysis
            scenario_codes = analysis_result.get('scenarios', [])
            rationales = analysis_result.get('rationales', {})
            provider_items = analysis_result.get('provider_items', [])

            current_app.logger.info(f"Claude identified scenarios: {scenario_codes}")
            current_app.logger.info(f"Claude identified {len(provider_items)} provider-recommended items")

            if not scenario_codes and not provider_items:
                return jsonify({
                    'error': 'No clinical scenarios or provider recommendations were identified. '
                             'Please ensure the medical summary contains structural diagnoses '
                             '(herniations, tears, fractures, etc.) or upload treating provider recommendations.'
                }), 400

            # Phase 2: Map scenarios to items with costs (deterministic)
            cost_data = scenarios_to_cost_data(
                scenario_codes,
                workbook_data,
                rationales,
                provider_items=provider_items
            )

            # Store analysis results for potential display
            cost_data['analysis'] = {
                'scenarios': scenario_codes,
                'diagnoses': analysis_result.get('diagnoses', []),
                'provider_items': provider_items,
                'summary': analysis_result.get('summary', '')
            }

        else:
            # TRADITIONAL MODE: Use pre-checked items from workbook
            current_app.logger.info("Traditional mode: Using pre-checked items from workbook")
            workbook_data = parse_workbook(workbook_path)
            cost_data = calculate_all_costs(workbook_data)

        # Generate document
        patient_name = workbook_data['patient_info'].get('patient_name', 'Unknown')
        safe_name = "".join(c for c in patient_name if c.isalnum() or c in ' -_').strip()
        doc_filename = f"LCP_Recommendations_{safe_name}_{uuid.uuid4().hex[:8]}.docx"
        doc_path = os.path.join(temp_dir, doc_filename)

        generate_lcp_document(
            workbook_data['patient_info'],
            cost_data,
            doc_path
        )

        # Try to save to Supabase (optional - works without it)
        case_id = None
        try:
            case = save_case(workbook_data['patient_info'], cost_data['totals'])
            if case:
                case_id = case['id']
                save_case_items(case_id, cost_data['items'])

                # Upload document to storage
                storage_path = f"cases/{case_id}/{doc_filename}"
                upload_file_to_storage(doc_path, storage_path)
                save_document_metadata(
                    case_id,
                    doc_filename,
                    storage_path,
                    os.path.getsize(doc_path)
                )
        except Exception as e:
            # Supabase save failed, but we can still return the document
            current_app.logger.warning(f"Supabase save failed: {str(e)}")

        # Return the generated document
        return send_file(
            doc_path,
            as_attachment=True,
            download_name=doc_filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except NoItemsSelectedError as e:
        return jsonify({'error': str(e)}), 400
    except MissingPatientInfoError as e:
        return jsonify({'error': str(e)}), 400
    except WorkbookParseError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error generating LCP: {str(e)}")
        return jsonify({'error': f'Error processing workbook: {str(e)}'}), 500
    finally:
        # Cleanup temp files
        try:
            if os.path.exists(workbook_path):
                os.remove(workbook_path)
            if medical_summary_path and os.path.exists(medical_summary_path):
                os.remove(medical_summary_path)
            if provider_recommendations_path and os.path.exists(provider_recommendations_path):
                os.remove(provider_recommendations_path)
        except Exception:
            pass


@api_bp.route('/preview', methods=['POST'])
def preview_lcp():
    """
    Preview LCP data without generating document.

    Returns cost calculations and summary without saving.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    temp_dir = tempfile.mkdtemp()
    filename = secure_filename(file.filename)
    workbook_path = os.path.join(temp_dir, filename)
    file.save(workbook_path)

    try:
        workbook_data = parse_workbook(workbook_path)
        cost_data = calculate_all_costs(workbook_data)

        return jsonify({
            'patient_info': {
                'patient_name': workbook_data['patient_info'].get('patient_name'),
                'date_of_birth': str(workbook_data['patient_info'].get('date_of_birth', '')),
                'date_of_injury': str(workbook_data['patient_info'].get('date_of_injury', '')),
                'life_expectancy': workbook_data['patient_info'].get('life_expectancy'),
            },
            'totals': cost_data['totals'],
            'categories': {
                cat: {
                    'annual_cost': data['annual_cost'],
                    'one_time_cost': data['one_time_cost'],
                    'item_count': len(data['items'])
                }
                for cat, data in cost_data['category_totals'].items()
            },
            'item_count': len(cost_data['items']),
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        try:
            if os.path.exists(workbook_path):
                os.remove(workbook_path)
        except Exception:
            pass


@api_bp.route('/cases', methods=['GET'])
def list_cases():
    """List all cases."""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        cases = get_cases(limit, offset)
        return jsonify({'cases': cases})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/cases/<case_id>', methods=['GET'])
def get_case_detail(case_id):
    """Get case details by ID."""
    try:
        case = get_case(case_id)
        if not case:
            return jsonify({'error': 'Case not found'}), 404

        items = get_case_items(case_id)
        documents = get_documents(case_id)

        return jsonify({
            'case': case,
            'items': items,
            'documents': documents
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/documents/<case_id>/download', methods=['GET'])
def download_document(case_id):
    """Get download URL for case document."""
    try:
        documents = get_documents(case_id)
        if not documents:
            return jsonify({'error': 'No documents found'}), 404

        # Get most recent document
        doc = documents[0]
        download_url = get_download_url(doc['storage_path'])

        return jsonify({
            'download_url': download_url,
            'file_name': doc['file_name']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# CLINICAL RULES MANAGEMENT API
# =============================================================================

@api_bp.route('/rules', methods=['GET'])
def get_rules():
    """
    List all clinical decision rules.

    Query params:
        - include_inactive: bool (default false)
    """
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        rules = list_all_rules(include_inactive=include_inactive)
        return jsonify({'rules': rules})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/rules', methods=['POST'])
def create_rule():
    """
    Add a new clinical decision rule.

    JSON body:
        - category: str (required) - 'general', 'age', 'treatment_history', 'diagnosis', 'body_part'
        - rule_name: str (required)
        - condition_description: str (required) - When this rule applies
        - action_description: str (required) - What to do when condition is met
        - subcategory: str (optional) - e.g., 'cervical', 'lumbar'
        - priority: int (optional, default 100) - Higher = applied first
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        required_fields = ['category', 'rule_name', 'condition_description', 'action_description']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        rule = add_rule(
            category=data['category'],
            rule_name=data['rule_name'],
            condition_description=data['condition_description'],
            action_description=data['action_description'],
            subcategory=data.get('subcategory'),
            priority=data.get('priority', 100)
        )

        if rule:
            return jsonify({'rule': rule, 'message': 'Rule created successfully'}), 201
        else:
            return jsonify({'error': 'Failed to create rule. Check Supabase configuration.'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/rules/<rule_id>', methods=['PUT'])
def modify_rule(rule_id):
    """
    Update an existing rule.

    JSON body can include any of:
        - rule_name, condition_description, action_description
        - category, subcategory, priority, is_active
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        # Only allow certain fields to be updated
        allowed_fields = [
            'rule_name', 'condition_description', 'action_description',
            'category', 'subcategory', 'priority', 'is_active'
        ]
        updates = {k: v for k, v in data.items() if k in allowed_fields}

        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400

        rule = update_rule(rule_id, updates)

        if rule:
            return jsonify({'rule': rule, 'message': 'Rule updated successfully'})
        else:
            return jsonify({'error': 'Failed to update rule'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/rules/<rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    """
    Deactivate a rule (soft delete).

    The rule is not permanently deleted, just marked as inactive.
    """
    try:
        success = deactivate_rule(rule_id)

        if success:
            return jsonify({'message': 'Rule deactivated successfully'})
        else:
            return jsonify({'error': 'Failed to deactivate rule'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# SCENARIOS API (Read-only for admin panel)
# =============================================================================

@api_bp.route('/scenarios', methods=['GET'])
def get_scenarios():
    """
    List all clinical scenarios.

    Returns scenario codes, names, and descriptions from the scenario bundles.
    """
    try:
        from app.services.scenario_bundles import SCENARIO_BUNDLES

        scenarios = []
        for code, bundle in SCENARIO_BUNDLES.items():
            # Determine body region from code prefix
            region_map = {
                'C': 'Cervical Spine',
                'T': 'Thoracic Spine',
                'L': 'Lumbar Spine',
                'S': 'Shoulder',
                'E': 'Elbow',
                'W': 'Wrist/Hand',
                'H': 'Hip',
                'K': 'Knee',
                'F': 'Foot/Ankle'
            }
            prefix = code[0] if code else ''
            body_region = region_map.get(prefix, 'Other')

            scenarios.append({
                'code': code,
                'name': bundle.get('name', ''),
                'description': bundle.get('description', ''),
                'body_region': body_region,
                'item_count': len(bundle.get('items', []))
            })

        # Sort by code
        scenarios.sort(key=lambda x: (x['body_region'], x['code']))

        return jsonify({'scenarios': scenarios})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/scenarios/<code>', methods=['GET'])
def get_scenario_detail(code):
    """
    Get detailed information about a specific scenario.

    Returns the scenario bundle including all items.
    """
    try:
        from app.services.scenario_bundles import get_scenario

        scenario = get_scenario(code)
        if not scenario:
            return jsonify({'error': 'Scenario not found'}), 404

        return jsonify({'scenario': scenario})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# KNOWLEDGE BASE API (Document Upload & Memory)
# =============================================================================

@api_bp.route('/knowledge-base/upload', methods=['POST'])
def upload_knowledge_base():
    """
    Upload a Word document to be parsed as clinical preferences.

    This gives Claude "memory" of Dr. Tontz's preferences.
    The document is parsed by Claude and the extracted rules
    are stored for use in future analyses.

    Expects multipart/form-data with:
        - file: Word document (.docx)
        - document_type: optional (default: 'master_preferences')
        - import_rules: optional bool (default: true) - also add to clinical_rules
    """
    from app.services.knowledge_base import (
        extract_text_from_docx,
        parse_preferences_with_claude,
        save_knowledge_base,
        import_rules_from_knowledge_base
    )

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.docx'):
        return jsonify({'error': 'Please upload a Word document (.docx)'}), 400

    # Save uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    filename = secure_filename(file.filename)
    file_path = os.path.join(temp_dir, filename)
    file.save(file_path)

    try:
        # Extract text from document
        current_app.logger.info(f"Extracting text from {filename}")
        raw_text = extract_text_from_docx(file_path)

        if not raw_text or len(raw_text) < 100:
            return jsonify({'error': 'Document appears to be empty or too short'}), 400

        # Parse with Claude
        current_app.logger.info("Parsing document with Claude...")
        parsed_content = parse_preferences_with_claude(raw_text)

        if parsed_content.get('error'):
            return jsonify({
                'error': f"Parsing error: {parsed_content['error']}",
                'raw_response': parsed_content.get('raw_response', '')
            }), 400

        # Save to Supabase
        document_type = request.form.get('document_type', 'master_preferences')
        saved = save_knowledge_base(filename, raw_text, parsed_content, document_type)

        # Optionally import as clinical rules
        import_rules = request.form.get('import_rules', 'true').lower() == 'true'
        rules_imported = 0
        if import_rules:
            rules_imported = import_rules_from_knowledge_base(parsed_content)

        # Count extracted rules
        rule_counts = {
            'global_principles': len(parsed_content.get('global_principles', [])),
            'spine_rules': len(parsed_content.get('spine_rules', [])),
            'upper_extremity_rules': len(parsed_content.get('upper_extremity_rules', [])),
            'lower_extremity_rules': len(parsed_content.get('lower_extremity_rules', [])),
            'treatment_rules': len(parsed_content.get('treatment_rules', [])),
            'age_rules': len(parsed_content.get('age_rules', [])),
            'imaging_rules': len(parsed_content.get('imaging_rules', []))
        }
        total_rules = sum(rule_counts.values())

        return jsonify({
            'success': True,
            'message': f'Document parsed successfully! Extracted {total_rules} rules.',
            'document_name': filename,
            'summary': parsed_content.get('raw_summary', ''),
            'rule_counts': rule_counts,
            'total_rules': total_rules,
            'rules_imported_to_clinical_rules': rules_imported,
            'saved_to_knowledge_base': saved is not None
        })

    except Exception as e:
        current_app.logger.error(f"Error processing knowledge base upload: {str(e)}")
        return jsonify({'error': f'Error processing document: {str(e)}'}), 500
    finally:
        # Cleanup
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


@api_bp.route('/knowledge-base', methods=['GET'])
def get_knowledge_base():
    """
    Get the current active knowledge base content.
    """
    from app.services.knowledge_base import get_active_knowledge_base

    try:
        kb = get_active_knowledge_base()
        if not kb:
            return jsonify({
                'active': False,
                'message': 'No knowledge base uploaded yet. Upload a preferences document to get started.'
            })

        return jsonify({
            'active': True,
            'document_name': kb.get('document_name'),
            'document_type': kb.get('document_type'),
            'version': kb.get('version'),
            'created_at': kb.get('created_at'),
            'summary': kb.get('raw_summary'),
            'parsed_content': kb.get('parsed_content')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/knowledge-base/history', methods=['GET'])
def get_knowledge_base_history():
    """
    Get history of all knowledge base uploads.
    """
    from app.services.knowledge_base import get_knowledge_base_history

    try:
        history = get_knowledge_base_history()
        return jsonify({'history': history})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
