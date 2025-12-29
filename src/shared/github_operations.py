"""
GitHub operations for creating fix PRs
"""

import os
import logging
from github import Github, GithubException
from typing import Dict, Optional


class GitHubOperations:
    """Handle GitHub operations for auto-fix PRs"""
    
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        
        if not self.token:
            raise ValueError("GITHUB_TOKEN must be set")
        
        self.client = Github(self.token)
        logging.info("GitHub client initialized")
        
    async def create_fix_pr(
        self,
        repo_owner: str,
        repo_name: str,
        source_branch: str,
        fix_description: str,
        file_changes: Dict[str, str],
        rca: dict
    ) -> dict:
        """
        Create a PR with the suggested fix
        
        Args:
            repo_owner: GitHub username/org (e.g., "opscart")
            repo_name: Repository name (e.g., "agentic-devops-healing")
            source_branch: Base branch (e.g., "main")
            fix_description: Description of the fix
            file_changes: Dict of {file_path: new_content}
            rca: Root cause analysis details
        
        Returns:
            dict with PR details
        """
        try:
            # Get repository
            repo_full_name = f"{repo_owner}/{repo_name}"
            repo = self.client.get_repo(repo_full_name)
            
            logging.info(f"Connected to GitHub repo: {repo_full_name}")
            # Handle special refs (PR merge refs, etc.)
            if source_branch.startswith('refs/pull/'):
                # This is a PR validation run - use main as base
                logging.warning(f"Detected PR merge ref: {source_branch}")
                logging.info("Using 'main' as base branch instead")
                source_branch = 'main'
            elif source_branch.startswith('refs/heads/'):
                # Remove refs/heads/ prefix
                source_branch = source_branch.replace('refs/heads/', '')
            
            # Create fix branch name
            category = rca.get('category', 'fix').lower().replace('_', '-')
            fix_branch_name = f"auto-fix/{category}-{os.urandom(4).hex()}"
            
            logging.info(f"Creating branch: {fix_branch_name} from {source_branch}")
            
            # Get base branch reference
            try:
                base_ref = repo.get_git_ref(f"heads/{source_branch}")
                base_sha = base_ref.object.sha
            except GithubException as e:
                if e.status == 404:
                    # Branch not found, default to main
                    logging.warning(f"⚠️ Branch '{source_branch}' not found, using 'main'")
                    base_ref = repo.get_git_ref("heads/main")
                    base_sha = base_ref.object.sha
                    source_branch = 'main'
                else:
                    raise
            
            # Create new branch
            repo.create_git_ref(
                ref=f"refs/heads/{fix_branch_name}",
                sha=base_sha
            )
            
            logging.info(f"Branch created: {fix_branch_name}")
            
            # Track if we made any commits
            commits_made = False
            
            # If we have file changes, apply them
            if file_changes and len(file_changes) > 0:
                logging.info(f"Applying {len(file_changes)} file change(s)")
                
                for file_path, new_content in file_changes.items():
                    try:
                        # Try to get existing file
                        contents = repo.get_contents(file_path, ref=fix_branch_name)
                        
                        # Update existing file
                        repo.update_file(
                            path=file_path,
                            message=f"Auto-fix: {rca.get('category', 'Fix issue')}",
                            content=new_content,
                            sha=contents.sha,
                            branch=fix_branch_name
                        )
                        logging.info(f"Updated file: {file_path}")
                        commits_made = True
                        
                    except GithubException as e:
                        if e.status == 404:
                            # File doesn't exist, create it
                            repo.create_file(
                                path=file_path,
                                message=f"Auto-fix: Add {file_path}",
                                content=new_content,
                                branch=fix_branch_name
                            )
                            logging.info(f"Created file: {file_path}")
                            commits_made = True
                        else:
                            raise
            
            # If no file changes provided, create a documentation commit
            if not commits_made:
                logging.info("No file changes provided - creating fix suggestion document")
                
                # Create a placeholder file with the fix suggestion
                placeholder_content = f"""# Auto-Fix Suggestion

**Category:** {rca.get('category', 'Unknown')}
**Confidence:** {rca.get('confidence', 0) * 100:.0f}%

## Root Cause Analysis

{fix_description}

## Suggested Implementation

Please review the analysis above and implement the necessary changes.

## Next Steps

1. Review this analysis
2. Implement the suggested fix
3. Test the changes
4. Update this PR with actual code changes
5. Request review and merge

---
*Auto-generated by Agentic DevOps Healing*
*This document will be replaced once actual code changes are committed*
"""
                
                # Create the documentation file
                doc_filename = f"fix-suggestion-{category}.md"
                repo.create_file(
                    path=f".agentic-devops/{doc_filename}",
                    message=f"Document auto-fix suggestion: {rca.get('category', 'Fix')}",
                    content=placeholder_content,
                    branch=fix_branch_name
                )
                logging.info(f"Created fix suggestion document: .agentic-devops/{doc_filename}")
                commits_made = True            
            # Create PR
            pr_title = f"Auto-fix: {rca.get('category', 'Pipeline Failure').replace('_', ' ').title()}"
            
            pr_body = f"""## Automated Fix by Agentic DevOps Healing

**Issue Detected:** {rca.get('category', 'Unknown')}  
**Confidence:** {rca.get('confidence', 0) * 100:.0f}%

### Root Cause Analysis

{fix_description}

### Changes Made

"""
            
            if file_changes:
                pr_body += "**Modified Files:**\n"
                for file_path in file_changes.keys():
                    pr_body += f"- `{file_path}`\n"
            else:
                pr_body += "*No file changes included - manual implementation required based on suggestions above.*\n"
            
            pr_body += """

---
*This PR was automatically generated by AI analysis of pipeline failure.*  
*Please review the changes carefully before merging.*

**Suggested Actions:**
1. Review the proposed changes
2. Run the pipeline to verify the fix
3. Merge if tests pass
"""
            
            # Create the pull request
            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=fix_branch_name,
                base=source_branch
            )
            
            logging.info(f"PR created: {pr.html_url}")
            
            # Add labels
            try:
                pr.add_to_labels("automated", "ai-generated")
                logging.info("Added labels to PR")
            except Exception as label_error:
                logging.warning(f"Could not add labels: {str(label_error)}")
            
            return {
                "pr_id": pr.number,
                "pr_url": pr.html_url,
                "title": pr_title,
                "branch": fix_branch_name,
                "status": "created"
            }
            
        except Exception as e:
            logging.error(f"Error creating GitHub PR: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            raise


    def get_repo_from_url(self, repo_url: str) -> tuple:
        """
        Extract owner and repo name from GitHub URL
        
        Args:
            repo_url: Full GitHub URL
            
        Returns:
            Tuple of (owner, repo_name)
        """
        if not repo_url:
            return None, None
            
        # Handle various GitHub URL formats
        # https://github.com/owner/repo
        # https://github.com/owner/repo.git
        # git@github.com:owner/repo.git
        
        if 'github.com' in repo_url:
            if repo_url.startswith('git@'):
                # SSH format: git@github.com:owner/repo.git
                parts = repo_url.split(':')[1].replace('.git', '').split('/')
            else:
                # HTTPS format: https://github.com/owner/repo
                parts = repo_url.replace('https://', '').replace('http://', '').replace('.git', '').split('/')
                parts = [p for p in parts if p and p != 'github.com']
            
            if len(parts) >= 2:
                return parts[0], parts[1]
        
        return None, None