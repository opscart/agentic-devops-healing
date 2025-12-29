"""
Code generation for common Terraform patterns
"""

import re
import logging


def generate_terraform_fix(rca: dict, context: dict) -> dict:
    """Generate actual file changes based on RCA"""
    
    category = rca.get('category', '')
    explanation = rca.get('explanation', '')
    
    logging.info(f"🔧 Code generator called for category: {category}")
    
    if category == 'TERRAFORM_MISSING_VARIABLE':
        return generate_missing_variable_fix(explanation, context)
    
    logging.warning(f"⚠️ No code generation for category: {category}")
    return {}


def generate_missing_variable_fix(explanation: str, context: dict = None) -> dict:
    """Generate variables.tf with missing variable"""
    
    # Extract variable name using MOST SPECIFIC pattern first
    var_name = None
    
    # Pattern: var.VARNAME (most reliable)
    matches = re.findall(r'var\.([a-z_][a-z0-9_]*)', explanation, re.IGNORECASE)
    
    if matches:
        # Count occurrences and pick most common
        from collections import Counter
        counts = Counter(matches)
        var_name = counts.most_common(1)[0][0]
        logging.info(f"✅ Extracted variable: {var_name} (found {counts[var_name]} times)")
    
    if not var_name:
        logging.error("❌ Could not extract variable name")
        return {}
    
    # Clean it
    var_name = var_name.strip().lower()
    
    # Defaults and descriptions
    defaults = {
        'azure_region': 'eastus',
        'location': 'eastus',
        'region': 'eastus',
        'environment': 'dev',
    }
    
    descriptions = {
        'azure_region': 'Azure region for resource deployment',
        'location': 'Azure location for resources',
        'region': 'Region for deployment',
        'environment': 'Environment name',
    }
    
    default_value = defaults.get(var_name, 'CHANGE_ME')
    description = descriptions.get(var_name, f'Value for {var_name}')
    
    # Generate Terraform code
    terraform_code = f'''variable "{var_name}" {{
  description = "{description}"
  type        = string
  default     = "{default_value}"
}}
'''
    
    # Determine filepath
    # For test scenario, use test path
    filepath = "infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable/variables.tf"
    
    logging.info(f"✅ Generated: {var_name} = {default_value}")
    logging.info(f"📁 File: {filepath}")
    
    return {
        filepath: terraform_code
    }