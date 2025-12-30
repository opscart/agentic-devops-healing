"""
Code generation for common Terraform patterns
"""

import re
import logging
from collections import Counter


def generate_terraform_fix(rca: dict, context: dict) -> dict:
    """Generate actual file changes based on RCA"""
    
    category = rca.get('category', '')
    logging.info(f"🔧 Generating fix for category: {category}")
    
    if category == 'TERRAFORM_MISSING_VARIABLE':
        return generate_missing_variable_fix(rca.get('explanation', ''), context)
    
    elif category == 'TERRAFORM_WRONG_REGION':
        return generate_region_fix(rca.get('explanation', ''), context)
    
    logging.warning(f"⚠️ No code generation implemented for category: {category}")
    return {}


def extract_variable_name(build_logs: str) -> str:
    """Extract variable name from build logs"""
    
    # Priority 1: Look for Terraform's error message
    # "An input variable with the name "azure_region" has not been declared"
    match = re.search(
        r'variable with the name ["\']([a-z_][a-z0-9_]*)["\']',
        build_logs,
        re.IGNORECASE
    )
    if match:
        var_name = match.group(1)
        logging.info(f"Extracted variable from error message: {var_name}")
        return var_name
    
    # Priority 2: Look for var.VARNAME pattern
    matches = re.findall(r'var\.([a-z_][a-z0-9_]*)', build_logs, re.IGNORECASE)
    if matches:
        # Get most common variable name
        var_name = Counter(matches).most_common(1)[0][0]
        logging.info(f"Extracted variable from var. pattern: {var_name}")
        return var_name
    
    logging.error("Could not extract variable name from logs")
    return None


def determine_filepath(context: dict, filename: str = 'variables.tf') -> str:
    """Determine the correct filepath from build logs"""
    
    build_logs = context.get('build_logs', '')
    
    if not build_logs:
        logging.error("❌ No build logs available")
        return f"infrastructure/core/terraform/{filename}"
    
    # Strategy 1: Look for explicit working directory output
    # The logs show: "Working directory: /home/vsts/work/1/s/infrastructure/..."
    match = re.search(
        r'Working directory:\s*/[^/]+/[^/]+/[^/]+/[^/]+/(infrastructure/[\w\-/]+)',
        build_logs,
        re.IGNORECASE
    )
    if match:
        rel_path = match.group(1)
        filepath = f"{rel_path}/{filename}"
        logging.info(f"✅ Extracted from 'Working directory': {filepath}")
        return filepath
    
    # Strategy 2: Look for cd command to Build.SourcesDirectory
    # Example: cd $(Build.SourcesDirectory)/infrastructure/test-apps/...
    match = re.search(
        r'cd.*?SourcesDirectory[^\n]*/?(infrastructure/test-apps/[\w\-/]+)',
        build_logs,
        re.IGNORECASE
    )
    if match:
        rel_path = match.group(1)
        filepath = f"{rel_path}/{filename}"
        logging.info(f"✅ Extracted from cd command: {filepath}")
        return filepath
    
    # Strategy 3: Look for terraform init/validate in specific directory
    # Find lines with "terraform init" and extract directory from context
    for i, line in enumerate(build_logs.split('\n')):
        if 'terraform init' in line.lower():
            # Look backwards for cd command
            for prev_line in build_logs.split('\n')[max(0, i-10):i]:
                match = re.search(r'cd.*/?(infrastructure/[\w\-/]+)', prev_line)
                if match:
                    rel_path = match.group(1)
                    filepath = f"{rel_path}/{filename}"
                    logging.info(f"✅ Extracted from terraform context: {filepath}")
                    return filepath
    
    # Fallback: Use failure_info if available
    failure_info = context.get('failure_info', {})
    pipeline_id = failure_info.get('pipeline_id', '')
    
    # Map known pipeline IDs (only for test scenarios)
    if pipeline_id in ['23', '24', '25']:
        test_scenarios = {
            '23': 'infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable',
            '24': 'infrastructure/test-apps/infra-only/terraform/scenarios/wrong-region',
            '25': 'infrastructure/test-apps/infra-only/terraform/scenarios/invalid-syntax',
        }
        if pipeline_id in test_scenarios:
            filepath = f"{test_scenarios[pipeline_id]}/{filename}"
            logging.warning(f"⚠️ Using fallback mapping for test pipeline {pipeline_id}: {filepath}")
            return filepath
    
    # Default
    logging.error("❌ Could not determine filepath from logs")
    return f"infrastructure/core/terraform/{filename}"


def generate_missing_variable_fix(explanation: str, context: dict) -> dict:
    """Generate fix for missing Terraform variable"""
    
    if not context:
        logging.error("No context provided")
        return {}
    
    build_logs = context.get('build_logs', '')
    if not build_logs:
        logging.error("No build logs in context")
        return {}
    
    # Extract variable name
    var_name = extract_variable_name(build_logs)
    if not var_name:
        logging.error("Cannot generate fix without variable name")
        return {}
    
    # Generate Terraform variable block
    defaults = {
        'azure_region': 'eastus',
        'location': 'eastus',
        'region': 'eastus',
        'environment': 'dev',
    }
    
    descriptions = {
        'azure_region': 'Azure region for resource deployment',
        'location': 'Azure location for resources',
        'region': 'Deployment region',
        'environment': 'Environment name',
    }
    
    default_value = defaults.get(var_name, 'CHANGE_ME')
    description = descriptions.get(var_name, f'Value for {var_name}')
    
    terraform_code = f'''variable "{var_name}" {{
  description = "{description}"
  type        = string
  default     = "{default_value}"
}}
'''
    
    # Determine filepath
    filepath = determine_filepath(context, 'variables.tf')
    
    logging.info(f"Generated variable: {var_name} = {default_value}")
    logging.info(f"Target file: {filepath}")
    
    return {
        filepath: terraform_code
    }


def generate_region_fix(explanation: str, context: dict) -> dict:
    """
    Generate fix for wrong Azure region.
    Note: This requires fetching and modifying existing main.tf
    Currently not implemented.
    """
    
    logging.warning("Region fix not yet implemented")
    return {}

def generate_region_fix(explanation: str, context: dict) -> dict:
    """Generate fix for wrong Azure region"""
    
    if not context:
        logging.error("No context provided")
        return {}
    
    build_logs = context.get('build_logs', '')
    if not build_logs:
        logging.error("No build logs")
        return {}
    
    # Extract wrong region from Terraform error
    # Pattern: "east-us" was not found in the list of supported Azure Locations
    match = re.search(r'"([a-z]+-[a-z-]+)" was not found', build_logs, re.IGNORECASE)
    if not match:
        logging.error("Could not extract wrong region from logs")
        return {}
    
    wrong_region = match.group(1)
    correct_region = wrong_region.replace('-', '')  # east-us → eastus
    
    logging.info(f"🔧 Region fix: '{wrong_region}' → '{correct_region}'")
    
    # Determine filepath (main.tf not variables.tf)
    filepath = determine_filepath(context, 'main.tf')
    
    # Fetch current main.tf content from GitHub
    try:
        from github import Github
        import os
        
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logging.error("GITHUB_TOKEN not set")
            return {}
        
        g = Github(github_token)
        repo = g.get_repo("opscart/agentic-devops-healing")
        
        # Get the file
        file_content = repo.get_contents(filepath, ref="main")
        current_code = file_content.decoded_content.decode('utf-8')
        
        logging.info(f"Fetched {filepath} from GitHub")
        
        # Replace wrong region with correct one
        # Look for location = "east-us"
        fixed_code = re.sub(
            rf'location\s*=\s*"{re.escape(wrong_region)}"',
            f'location = "{correct_region}"',
            current_code,
            flags=re.IGNORECASE
        )
        
        if fixed_code == current_code:
            logging.error("No changes made - pattern not found")
            return {}
        
        logging.info(f"Fixed region in code")
        
        return {
            filepath: fixed_code
        }
        
    except Exception as e:
        logging.error(f"Error fetching/fixing file: {str(e)}")
        return {}