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


def extract_terraform_error(build_logs: str) -> str:
    """Extract the specific Terraform error message"""
    # Look for "Error:" lines
    error_pattern = r'Error: (.+?)(?:\n|$)'
    matches = re.findall(error_pattern, build_logs, re.MULTILINE)
    
    if matches:
        return matches[0]
    
    return "Unknown Terraform error"


async def analyze_terraform_failure(context: Dict, openai_client) -> Dict:
    """
    Analyze Terraform-specific failures
    """
    build_logs = context.get('build_logs', '')
    last_success = context.get('last_success_logs', '')
    
    # Extract the specific error
    error_message = extract_terraform_error(build_logs)
    
    logging.info(f"Terraform error: {error_message}")
    
    # Check for common patterns
    if "Missing required variable" in error_message:
        return analyze_missing_variable(error_message, context)
    
    elif "Invalid location" in error_message or "invalid region" in error_message.lower():
        return analyze_invalid_region(error_message, context)
    
    else:
        # Use AI for complex analysis
        return await analyze_with_ai(error_message, build_logs, last_success, openai_client)


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
    error_message: str,
    build_logs: str,
    last_success: str,
    openai_client
) -> Dict:
    """Use AI for complex Terraform analysis"""
    
    system_message = """You are a Terraform expert analyzing pipeline failures.
Analyze the error and provide:
1. Root cause category
2. Confidence level (0.0-1.0)
3. Clear explanation
4. Whether it can be auto-fixed
5. Suggested fix

Be concise and specific."""
    
    prompt = f"""Analyze this Terraform failure:

ERROR MESSAGE:
{error_message}

RECENT BUILD LOGS:
{build_logs[:2000]}

Provide analysis in this format:
CATEGORY: [type]
CONFIDENCE: [0.0-1.0]
EXPLANATION: [brief explanation]
CAN_AUTOFIX: [true/false]
SUGGESTED_FIX: [what to do]
"""
    
    try:
        response = await openai_client.analyze(prompt, system_message)
        
        # Parse AI response (simple parsing for now)
        return {
            "category": "TERRAFORM_ERROR",
            "confidence": 0.7,
            "explanation": response,
            "can_autofix": False,
            "suggested_fix": "See AI analysis above"
        }
        
    except Exception as e:
        logging.error(f"AI analysis failed: {str(e)}")
        return {
            "category": "TERRAFORM_ERROR",
            "confidence": 0.5,
            "explanation": error_message,
            "can_autofix": False
        }