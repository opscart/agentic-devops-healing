"""
Agentic DevOps Healing - Infrastructure Healer Agent
Main Azure Function that handles pipeline failure webhooks
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime

app = func.FunctionApp()

################################################################################
# Webhook Handler - Entry Point
################################################################################

@app.function_name(name="HandleFailure")
@app.route(route="HandleFailure", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
async def handle_failure(req: func.HttpRequest) -> func.HttpResponse:
    """
    Receives webhook from Azure DevOps when pipeline fails.
    Triggered by failed pipeline task.
    """
    logging.info('Pipeline failure webhook received')
    
    try:
        # Parse request body
        req_body = req.get_json()
        
        # Extract failure context
        failure_context = {
            "timestamp": datetime.utcnow().isoformat(),
            "pipeline_id": req_body.get('pipelineId'),
            "build_id": req_body.get('buildId'),
            "build_number": req_body.get('buildNumber'),
            "pr_id": req_body.get('prId'),
            "failed_stage": req_body.get('failedStage'),
            "failed_job": req_body.get('failedJob'),
            "failed_task": req_body.get('failedTask'),
            "repo_url": req_body.get('repoUrl'),
            "source_branch": req_body.get('sourceBranch'),
            "project_name": req_body.get('projectName'),
            "organization_url": req_body.get('organizationUrl')
        }
        
        logging.info(f"Failure context: {json.dumps(failure_context, indent=2)}")
        
        # Validate required fields
        if not failure_context['build_id'] or not failure_context['project_name']:
            return func.HttpResponse(
                json.dumps({"error": "Missing required fields: buildId or projectName"}),
                mimetype="application/json",
                status_code=400
            )
        
        # TODO: In production, queue this for async processing
        # For now, we'll process synchronously for simplicity
        
        # Step 1: Gather context (logs, PR diff, etc.)
        logging.info("Gathering failure context...")
        context = await gather_failure_context(failure_context)
        
        # Step 2: Analyze with AI
        logging.info("Analyzing failure with OpenAI...")
        rca_result = await analyze_with_ai(context)
        
        # Step 3: Take action based on confidence
        logging.info("Executing remediation...")
        action_result = await execute_remediation(rca_result, failure_context)
        
        # Return response
        response = {
            "status": "success",
            "failure_context": failure_context,
            "rca": {
                "category": rca_result.get("category"),
                "confidence": rca_result.get("confidence"),
                "explanation": rca_result.get("explanation")
            },
            "action_taken": action_result.get("action"),
            "details": action_result.get("details")
        }
        
        logging.info(f"Processing complete: {response['action_taken']}")
        
        return func.HttpResponse(
            json.dumps(response, indent=2),
            mimetype="application/json",
            status_code=202
        )
        
    except ValueError as e:
        logging.error(f"Invalid JSON in request: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON payload"}),
            mimetype="application/json",
            status_code=400
        )
    
    except Exception as e:
        logging.error(f"Error processing failure: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


################################################################################
# Helper Functions
################################################################################

async def gather_failure_context(failure_info: dict) -> dict:
    """
    Gather all relevant context about the failure:
    - Build logs
    - Last successful build logs
    - PR changes (if applicable)
    - Pipeline YAML
    """
    from shared.ado_client import AzureDevOpsClient
    
    try:
        ado_client = AzureDevOpsClient()
        
        project = failure_info['project_name']
        build_id = failure_info['build_id']
        
        context = {
            "failure_info": failure_info,
            "build_logs": None,
            "last_success_logs": None,
            "pr_changes": None,
            "pipeline_yaml": None
        }
        
        # Get current build logs
        logging.info(f"Fetching build logs for build {build_id}...")
        context["build_logs"] = await ado_client.get_build_logs(project, build_id)
        
        # Get last successful build logs for comparison
        if failure_info.get('pipeline_id'):
            logging.info("Fetching last successful build logs...")
            context["last_success_logs"] = await ado_client.get_last_successful_build_logs(
                project,
                failure_info['pipeline_id'],
                failure_info.get('source_branch', 'refs/heads/main')
            )
        
        # Get PR changes if this is a PR build
        if failure_info.get('pr_id'):
            logging.info(f"Fetching PR changes for PR {failure_info['pr_id']}...")
            # Extract repo ID from URL
            repo_id = failure_info['repo_url'].split('/')[-1] if failure_info.get('repo_url') else None
            if repo_id:
                context["pr_changes"] = await ado_client.get_pr_changes(
                    project,
                    repo_id,
                    failure_info['pr_id']
                )
        
        # Get pipeline YAML (for YAML syntax errors)
        logging.info("Fetching pipeline definition...")
        context["pipeline_yaml"] = await ado_client.get_pipeline_yaml(
            project,
            failure_info.get('pipeline_id')
        )
        
        return context
        
    except Exception as e:
        logging.error(f"Error gathering context: {str(e)}")
        # Return partial context
        return {
            "failure_info": failure_info,
            "error": str(e)
        }


async def analyze_with_ai(context: dict) -> dict:
    """
    Use OpenAI to analyze the failure and determine root cause
    """
    from shared.openai_client import OpenAIClient
    from analyzers.terraform_analyzer import is_terraform_failure, extract_terraform_error
    from analyzers.pipeline_analyzer import is_pipeline_yaml_failure
    
    try:
        openai_client = OpenAIClient()
        
        # Quick classification: What type of failure is this?
        build_logs = context.get('build_logs', '')
        
        if is_terraform_failure(build_logs):
            logging.info("Detected Terraform failure")
            from analyzers.terraform_analyzer import analyze_terraform_failure
            return await analyze_terraform_failure(context, openai_client)
        
        elif is_pipeline_yaml_failure(build_logs):
            logging.info("Detected Pipeline YAML failure")
            from analyzers.pipeline_analyzer import analyze_yaml_failure
            return await analyze_yaml_failure(context, openai_client)
        
        else:
            # Generic analysis for unknown failure types
            logging.info("Performing generic failure analysis")
            return await generic_analysis(context, openai_client)
        
    except Exception as e:
        logging.error(f"Error in AI analysis: {str(e)}")
        return {
            "category": "UNKNOWN",
            "confidence": 0.0,
            "explanation": f"Failed to analyze: {str(e)}",
            "can_autofix": False
        }


async def generic_analysis(context: dict, openai_client) -> dict:
    """
    Generic analysis for unclassified failures
    """
    build_logs = context.get('build_logs', '')
    
    # Simple pattern matching for now
    if 'error' in build_logs.lower() or 'failed' in build_logs.lower():
        return {
            "category": "UNKNOWN_ERROR",
            "confidence": 0.3,
            "explanation": "Build failed but specific error type not recognized. Manual review required.",
            "can_autofix": False,
            "suggested_action": "Review build logs manually"
        }
    
    return {
        "category": "UNKNOWN",
        "confidence": 0.0,
        "explanation": "Unable to determine failure type",
        "can_autofix": False
    }


async def execute_remediation(rca_result: dict, failure_context: dict) -> dict:
    """
    Execute remediation based on RCA results:
    - HIGH confidence infrastructure issues: Create fix PR (GitHub or Azure Repos)
    - Everything else: Post detailed comment or create work item
    """
    import os
    from shared.ado_client import AzureDevOpsClient
    
    try:
        confidence = rca_result.get('confidence', 0.0)
        can_autofix = rca_result.get('can_autofix', False)
        category = rca_result.get('category', 'UNKNOWN')
        
        logging.info(f"Remediation decision: confidence={confidence}, can_autofix={can_autofix}, category={category}")
        
        ado_client = AzureDevOpsClient()
        
        # HIGH confidence + can autofix = Create PR
        if confidence >= 0.65 and can_autofix:
            logging.info("✨ High confidence - attempting auto-fix")
            
            # Determine if GitHub or Azure Repos
            repo_url = failure_context.get('repo_url', '')
            is_github = True  # Default to GitHub
            if repo_url:
                is_github = 'github.com' in repo_url.lower()
            
            if is_github:
                # GitHub PR Creation
                try:
                    from shared.github_operations import GitHubOperations
                    
                    github_ops = GitHubOperations()
                    
                    # Get repo details
                    repo_owner = os.getenv("GITHUB_REPO_OWNER", "opscart")
                    repo_name = os.getenv("GITHUB_REPO_NAME", "agentic-devops-healing")
                    
                    if repo_url:
                        extracted_owner, extracted_repo = github_ops.get_repo_from_url(repo_url)
                        if extracted_owner and extracted_repo:
                            repo_owner = extracted_owner
                            repo_name = extracted_repo
                    
                    # Get source branch
                    source_branch = failure_context.get('source_branch', 'main')
                    if source_branch and source_branch.startswith('refs/heads/'):
                        source_branch = source_branch.replace('refs/heads/', '')
                    if not source_branch:
                        source_branch = 'main'
                    
                    logging.info(f"🔧 Creating GitHub PR for {repo_owner}/{repo_name}, branch: {source_branch}")
                    
                    # Create the PR
                    pr_result = await github_ops.create_fix_pr(
                        repo_owner=repo_owner,
                        repo_name=repo_name,
                        source_branch=source_branch,
                        fix_description=rca_result.get('explanation', 'Auto-generated fix'),
                        file_changes={},
                        rca=rca_result
                    )
                    
                    pr_url = pr_result.get('pr_url', 'PR created')
                    pr_number = pr_result.get('pr_id', 'N/A')
                    pr_status = pr_result.get('status', 'created')
                    
                    # Check if it was a duplicate
                    if pr_status == 'duplicate_prevented':
                            logging.info(f"Found existing GitHub PR #{pr_number}: {pr_url}")
                            return {
                                "action": "EXISTING_PR_FOUND",  # ← Change action
                                "details": f"Found existing GitHub PR #{pr_number}",  # ← Change message
                                "pr_url": pr_url,
                                "pr_number": pr_number
                            }
                    else:
                        logging.info(f"GitHub PR #{pr_number} created: {pr_url}")
                        
                        return {
                            "action": "AUTO_FIX_PR_CREATED",
                            "details": f"Created GitHub PR #{pr_number}",
                            "pr_url": pr_url,
                            "pr_number": pr_number
                        }
                
                except Exception as pr_error:
                    logging.error(f"GitHub PR creation failed: {str(pr_error)}")
                    import traceback
                    logging.error(traceback.format_exc())
                    
                    # Fallback to work item
                    work_item_id = await ado_client.create_work_item(
                        project=failure_context.get('project_name', 'AI-DevOps-POC'),
                        title=f"🤖 Auto-fix Suggested: {category.replace('_', ' ').title()}",
                        description=f"PR creation failed: {str(pr_error)}\n\n{format_work_item_description(rca_result, failure_context)}"
                    )
                    
                    return {
                        "action": "AUTO_FIX_SUGGESTED",
                        "details": f"Created work item: {work_item_id} (PR failed: {str(pr_error)})",
                        "work_item_id": work_item_id
                    }
            
            else:
                # Azure Repos PR Creation
                try:
                    from shared.git_operations import GitOperations
                    
                    git_ops = GitOperations()
                    repo_name = "agentic-devops-healing"
                    
                    if repo_url and '/_git/' in repo_url:
                        repo_name = repo_url.split('/_git/')[-1].split('?')[0].strip('/')
                    
                    source_branch = failure_context.get('source_branch', 'refs/heads/main')
                    if not source_branch.startswith('refs/heads/'):
                        source_branch = f'refs/heads/{source_branch}'
                    
                    pr_result = await git_ops.create_fix_pr(
                        project=failure_context.get('project_name', 'AI-DevOps-POC'),
                        repo_name=repo_name,
                        source_branch=source_branch,
                        fix_description=rca_result.get('explanation', ''),
                        file_changes={},
                        rca=rca_result
                    )
                    
                    return {
                        "action": "AUTO_FIX_PR_CREATED",
                        "details": f"Created Azure PR",
                        "pr_url": pr_result.get('pr_url')
                    }
                
                except Exception as pr_error:
                    logging.error(f"Azure PR creation failed: {str(pr_error)}")
                    
                    work_item_id = await ado_client.create_work_item(
                        project=failure_context.get('project_name', 'AI-DevOps-POC'),
                        title=f"Pipeline Failure: {failure_context.get('failed_stage', 'Unknown')}",
                        description=format_work_item_description(rca_result, failure_context)
                    )
                    
                    return {
                        "action": "WORK_ITEM_CREATED",
                        "details": f"Created work item: {work_item_id} (PR failed)",
                        "work_item_id": work_item_id
                    }
        
        else:
            if confidence < 0.5:
                # Low confidence or can't autofix - create work item
                logging.warning(f"Confidence too low ({confidence}) - skipping work item creation")
                return {
                    "action": "SKIPPED",
                    "details": f"Analysis confidence too low ({confidence * 100:.0f}%) - manual investigation required",
                    "category": category,
                    "note": "No work item created due to low confidence"
                }
            # Create work item for medium confidence
            logging.info("Creating work item (confidence too low for auto-fix)")
            
            work_item_id = await ado_client.create_work_item(
                project=failure_context.get('project_name', 'AI-DevOps-POC'),
                title=f"Pipeline Failure: {failure_context.get('failed_stage', 'Unknown')}",
                description=format_work_item_description(rca_result, failure_context)
            )
            
            return {
                "action": "WORK_ITEM_CREATED",
                "details": f"Created work item: {work_item_id}",
                "work_item_id": work_item_id
            }
    
    except Exception as e:
        logging.error(f"Error in remediation: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return {
            "action": "ERROR",
            "details": str(e)
        }

def format_rca_comment(rca_result: dict) -> str:
    """Format RCA results as Markdown comment"""
    return f"""
## AI Root Cause Analysis

**Failure Category:** `{rca_result.get('category', 'UNKNOWN')}`  
**Confidence:** `{rca_result.get('confidence', 0.0):.0%}`

### Analysis
{rca_result.get('explanation', 'No explanation available')}

### Suggested Fix
{rca_result.get('suggested_fix', 'Manual review required')}

---
*Analyzed by Agentic DevOps Healer v0.1*
"""


def format_work_item_description(rca_result: dict, failure_context: dict) -> str:
    """Format work item description"""
    return f"""
## Pipeline Failure Analysis

**Build:** {failure_context.get('build_number', 'Unknown')}  
**Stage:** {failure_context.get('failed_stage', 'Unknown')}  
**Job:** {failure_context.get('failed_job', 'Unknown')}

## AI Analysis
**Category:** {rca_result.get('category', 'UNKNOWN')}  
**Confidence:** {rca_result.get('confidence', 0.0):.0%}

{rca_result.get('explanation', 'No explanation available')}

## Suggested Action
{rca_result.get('suggested_fix', 'Manual investigation required')}

## Build Link
{failure_context.get('organization_url', '')}/{failure_context.get('project_name', '')}/_build/results?buildId={failure_context.get('build_id', '')}
"""