"""
Terraform-specific failure analysis
"""

import re
import logging
from typing import Dict


def is_terraform_failure(build_logs: str) -> bool:
    """Detect if this is a Terraform failure"""
    terraform_keywords = [
        "terraform",
        "Error: Missing required variable",
        "Error: Invalid location",
        "Error: Unsupported argument",
        "Error: Reference to undeclared",
        "azurerm_"
    ]
    
    logs_lower = build_logs.lower()
    return any(keyword.lower() in logs_lower for keyword in terraform_keywords)

def detect_error_pattern(build_logs: str) -> tuple:
    """
    Detect specific Terraform error patterns
    Returns: (pattern_name, confidence_boost)
    """
    
    # Pattern 1: Missing Variable (highest priority)
    if 'Reference to undeclared input variable' in build_logs:
        return ('TERRAFORM_MISSING_VARIABLE', 0.95)
    
    # Pattern 2: Wrong Region
    if 'was not found in the list of supported Azure Locations' in build_logs:
        return ('TERRAFORM_WRONG_REGION', 0.90)
    
    # Pattern 3: Syntax Error
    if any(s in build_logs for s in ['Invalid character', 'Extra characters after interpolation', 'Missing closing brace']):
        return ('TERRAFORM_SYNTAX_ERROR', 0.95)
    
    return (None, None)


def extract_terraform_error(build_logs: str) -> str:
    """Extract the specific Terraform error message"""
    # Look for "Error:" lines
    error_pattern = r'Error: (.+?)(?:\n|$)'
    matches = re.findall(error_pattern, build_logs, re.MULTILINE)
    
    if matches:
        return matches[0]
    
    return "Unknown Terraform error"

def can_be_autofixed(error_message: str, category: str) -> bool:
    """
    Determine if this error can be safely auto-fixed
    
    Args:
        error_message: The error message from Terraform
        category: The error category
    
    Returns:
        bool: True if safe to auto-fix
    """
    error_lower = error_message.lower()
    
    # Definitely auto-fixable
    auto_fixable_patterns = [
        'variable .* was not set',
        'variable .* not defined',
        'missing required variable',
        'invalid region',
        'wrong region',
        'should be .* not .*',
        'expected .* got .*',
        'invalid location',
    ]
    
    for pattern in auto_fixable_patterns:
        if re.search(pattern, error_lower):
            return True
    
    # Definitely NOT auto-fixable
    manual_review_patterns = [
        'syntax error',
        'expected .* block',
        'missing closing brace',
        'unexpected token',
        'authentication failed',
        'state conflict',
        'state locked',
    ]
    
    for pattern in manual_review_patterns:
        if re.search(pattern, error_lower):
            return False
    
    # Default: safe errors are auto-fixable
    if category in ['TERRAFORM_MISSING_VARIABLE', 'TERRAFORM_WRONG_REGION']:
        return True
    
    # Default: uncertain errors need review
    return False

async def analyze_terraform_failure(failure_info: dict, openai_client) -> dict:
    """Analyze Terraform-specific failures"""
    
    build_logs = failure_info.get('build_logs', '')
    
    if not is_terraform_failure(build_logs):
        return None
    
    # Detect pattern BEFORE AI analysis
    pattern, pattern_confidence = detect_error_pattern(build_logs)
    
    if pattern:
        logging.info(f"🔍 Detected pattern: {pattern} (confidence: {pattern_confidence})")
    
    # Get AI analysis
    result = await analyze_with_ai(failure_info, openai_client)
    
    # Override AI if we have high-confidence pattern
    if pattern and pattern_confidence >= 0.90:
        ai_category = result.get('category', '')
        
        if ai_category != pattern:
            logging.warning(f"⚠️ AI said '{ai_category}', overriding to '{pattern}' based on pattern")
            result['category'] = pattern
            result['confidence'] = max(result.get('confidence', 0.7), pattern_confidence)
    
    # NOW use the corrected category
    category = result.get('category', 'TERRAFORM_ERROR')
    explanation = result.get('explanation', '').lower()
    
    # Check for syntax errors using CATEGORY (not explanation)
    is_syntax_error = (
        'SYNTAX' in category.upper() or  # ← Check category first
        category == 'TERRAFORM_SYNTAX_ERROR'  # ← Explicit check
    )
    
    # Only check explanation if category isn't clear
    if not is_syntax_error:
        is_syntax_error = (
            'syntax error' in explanation and
            'missing closing brace' in explanation or
            'invalid character' in explanation
        )
    
    if is_syntax_error:
        result['can_autofix'] = False
        logging.info(f"🔧 Auto-fix denied: Syntax error detected")
    else:
        # Check for safe auto-fixable patterns
        AUTO_FIXABLE = [
            'TERRAFORM_MISSING_VARIABLE',
            'TERRAFORM_WRONG_REGION',
            'TERRAFORM_WRONG_VALUE',
            'Configuration Error'
        ]
        
        can_autofix = (
            category in AUTO_FIXABLE or
            ('missing' in explanation and 'variable' in explanation) or
            ('wrong region' in explanation) or
            ('invalid region' in explanation)
        )
        
        result['can_autofix'] = can_autofix
        logging.info(f"🔧 Auto-fix decision: {can_autofix} (category: {category})")
    
    return result


def analyze_missing_variable(error_message: str, context: Dict) -> Dict:
    """Analyze missing Terraform variable error"""
    # Extract variable name from error
    var_pattern = r'variable "([^"]+)"'
    match = re.search(var_pattern, error_message)
    
    if match:
        var_name = match.group(1)
        
        return {
            "category": "TERRAFORM_MISSING_VARIABLE",
            "confidence": 0.95,
            "explanation": f"Terraform requires variable '{var_name}' which is not defined in the pipeline.",
            "can_autofix": True,
            "fix_code": generate_variable_fix(var_name),
            "suggested_fix": f"Add 'TF_VAR_{var_name}' to pipeline variables"
        }
    
    return {
        "category": "TERRAFORM_MISSING_VARIABLE",
        "confidence": 0.6,
        "explanation": "Terraform variable missing, but could not extract variable name",
        "can_autofix": False
    }


def analyze_invalid_region(error_message: str, context: Dict) -> Dict:
    """Analyze invalid Azure region error"""
    return {
        "category": "TERRAFORM_INVALID_REGION",
        "confidence": 0.85,
        "explanation": f"Invalid Azure region specified. Error: {error_message}",
        "can_autofix": True,
        "fix_code": "# Fix: Use valid region like 'eastus', 'westus2', etc.",
        "suggested_fix": "Update 'location' parameter to valid Azure region"
    }


def generate_variable_fix(var_name: str) -> str:
    """Generate YAML fix for missing variable"""
    return f"""# Add to azure-pipelines.yml

variables:
  - name: TF_VAR_{var_name}
    value: 'UPDATE_THIS_VALUE'
"""


async def analyze_with_ai(
    failure_info: dict,
    openai_client
) -> dict:
    """Use OpenAI to analyze Terraform failure"""
    
    build_logs = failure_info.get('build_logs', '')
    
    # CRITICAL: Extract the relevant error section, not the entire log
    # Terraform errors appear at the END of logs, not the beginning
    if len(build_logs) > 10000:
        # Get last 5000 chars where actual errors are
        relevant_logs = build_logs[-5000:]
        logging.info(f"📋 Using last 5000 chars of {len(build_logs)} total chars")
    else:
        relevant_logs = build_logs
        logging.info(f"📋 Using all {len(build_logs)} chars (short log)")
    
    prompt = f"""
Analyze this Terraform pipeline failure and provide a structured response.

Build Logs (Error Section):
{relevant_logs}

Provide your analysis in this EXACT format:
CATEGORY: <one of: Configuration Error, Syntax Error, Authentication Error, State Error, Provider Error>
CONFIDENCE: <0.0 to 1.0>
EXPLANATION: <detailed explanation of what went wrong>
CAN_AUTOFIX: <True or False>
SUGGESTED_FIX: <specific steps to fix>

Guidelines for CAN_AUTOFIX:
- True for: Missing variables, wrong values, incorrect region names
- False for: Syntax errors, authentication issues, state conflicts

Be specific and actionable. Focus on the Terraform error, not the pipeline YAML.
"""
    
    system_message = """You are an expert DevOps engineer specializing in Terraform and infrastructure as code. 
Analyze pipeline failures and provide accurate root cause analysis with actionable fixes.

For CAN_AUTOFIX decision:
- Set to True if the fix is a simple configuration change (adding a variable, fixing a value, correcting a region name)
- Set to False if the fix requires human judgment (syntax errors, authentication, state management)

Focus on Terraform errors in the logs, not the pipeline definition itself.
"""
    
    try:
        response = await openai_client.analyze(prompt, system_message)
        
        # Parse the response
        category = "TERRAFORM_ERROR"
        confidence = 0.7
        explanation = response
        can_autofix = False
        
        # Extract structured fields
        for line in response.split('\n'):
            if line.startswith('CATEGORY:'):
                category_text = line.replace('CATEGORY:', '').strip()
                # Map to our categories
                if 'configuration' in category_text.lower():
                    category = "TERRAFORM_MISSING_VARIABLE"
                elif 'syntax' in category_text.lower():
                    category = "TERRAFORM_SYNTAX_ERROR"
                    
            elif line.startswith('CONFIDENCE:'):
                try:
                    confidence = float(line.replace('CONFIDENCE:', '').strip())
                except:
                    confidence = 0.7
                    
            elif line.startswith('CAN_AUTOFIX:'):
                autofix_text = line.replace('CAN_AUTOFIX:', '').strip().lower()
                can_autofix = autofix_text in ['true', 'yes', '1']
        
        # Smart overrides based on error patterns
        explanation_lower = explanation.lower()
        
        # Missing variable pattern
        if 'missing' in explanation_lower and 'variable' in explanation_lower:
            can_autofix = True
            category = "TERRAFORM_MISSING_VARIABLE"
            confidence = max(confidence, 0.85)
        
        # Wrong region/value pattern
        if any(word in explanation_lower for word in ['wrong region', 'invalid region', 'incorrect region', 'not found in the list']):
            can_autofix = True
            category = "TERRAFORM_WRONG_REGION"
            confidence = max(confidence, 0.85)
        
        # Syntax error pattern - NEVER autofix
        if any(word in explanation_lower for word in ['syntax error', 'missing brace', 'invalid character', 'unexpected token']):
            can_autofix = False
            category = "TERRAFORM_SYNTAX_ERROR"
            confidence = max(confidence, 0.90)
        
        return {
            "category": category,
            "confidence": min(confidence, 0.95),  # Cap at 0.95
            "explanation": explanation,
            "can_autofix": can_autofix
        }
        
    except Exception as e:
        logging.error(f"Error in AI analysis: {str(e)}")
        return {
            "category": "UNKNOWN_ERROR",
            "confidence": 0.3,
            "explanation": f"Error analyzing with AI: {str(e)}",
            "can_autofix": False
        }