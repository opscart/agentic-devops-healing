"""
Azure DevOps API Client
Handles all interactions with Azure DevOps REST API
"""

import os
import logging
from typing import Optional, Dict, List
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication


class AzureDevOpsClient:
    """Client for Azure DevOps operations"""
    
    def __init__(self):
        self.organization_url = os.getenv("ADO_ORG_URL")
        self.pat = os.getenv("ADO_PAT")
        
        if not self.organization_url or not self.pat:
            raise ValueError("ADO_ORG_URL and ADO_PAT must be set")
        
        credentials = BasicAuthentication('', self.pat)
        self.connection = Connection(base_url=self.organization_url, creds=credentials)
        
        self.build_client = self.connection.clients.get_build_client()
        self.git_client = self.connection.clients.get_git_client()
        self.work_item_client = self.connection.clients.get_work_item_tracking_client()
    
    async def get_build_logs(self, project: str, build_id: int) -> str:
        """Fetch complete build logs"""
        try:
            logs = self.build_client.get_build_logs(project, build_id)
            
            full_log = []
            for log in logs:
                try:
                    log_content = self.build_client.get_build_log(
                        project, build_id, log.id
                    )
                    full_log.append(log_content)
                except Exception as e:
                    logging.warning(f"Could not fetch log {log.id}: {str(e)}")
            
            return "\n".join(full_log)
            
        except Exception as e:
            logging.error(f"Error fetching build logs: {str(e)}")
            return ""
    
    async def get_last_successful_build_logs(
        self, 
        project: str, 
        pipeline_id: int, 
        branch: str
    ) -> str:
        """Get logs from last successful build on same branch"""
        try:
            builds = self.build_client.get_builds(
                project=project,
                definitions=[pipeline_id],
                branch_name=branch,
                result_filter='succeeded',
                top=1
            )
            
            if builds and len(builds) > 0:
                return await self.get_build_logs(project, builds[0].id)
            
            return ""
            
        except Exception as e:
            logging.error(f"Error fetching last successful build: {str(e)}")
            return ""
    
    async def get_pr_changes(
        self, 
        project: str, 
        repo_id: str, 
        pr_id: int
    ) -> Dict:
        """Get PR diff and metadata"""
        try:
            pr = self.git_client.get_pull_request(repo_id, pr_id, project)
            
            # Get commits
            commits = self.git_client.get_pull_request_commits(
                repo_id, pr_id, project
            )
            
            # Get file changes
            iterations = self.git_client.get_pull_request_iterations(
                repo_id, pr_id, project
            )
            
            changes = []
            if iterations and len(iterations) > 0:
                iteration_changes = self.git_client.get_pull_request_iteration_changes(
                    repo_id, pr_id, iterations[-1].id, project
                )
                if iteration_changes and iteration_changes.change_entries:
                    changes = iteration_changes.change_entries
            
            return {
                "title": pr.title,
                "description": pr.description,
                "author": pr.created_by.display_name if pr.created_by else "Unknown",
                "commits": [c.comment for c in commits] if commits else [],
                "files_changed": [
                    {
                        "path": change.item.path if change.item else "unknown",
                        "change_type": str(change.change_type) if change.change_type else "unknown"
                    } for change in changes
                ]
            }
            
        except Exception as e:
            logging.error(f"Error fetching PR changes: {str(e)}")
            return {}
    
    async def get_pipeline_yaml(self, project: str, pipeline_id: int) -> str:
        """Get pipeline YAML definition"""
        try:
            # This is a simplified version - actual implementation would
            # need to fetch the YAML file from the repository
            return ""
        except Exception as e:
            logging.error(f"Error fetching pipeline YAML: {str(e)}")
            return ""
    
    async def post_pr_comment(
        self, 
        project: str, 
        repo_id: str, 
        pr_id: int, 
        comment: str
    ) -> bool:
        """Post a comment on a Pull Request"""
        try:
            from azure.devops.v7_0.git.models import Comment, CommentThread
            
            thread = CommentThread(
                comments=[Comment(content=comment)],
                status=1  # Active
            )
            
            self.git_client.create_thread(
                comment_thread=thread,
                repository_id=repo_id,
                pull_request_id=pr_id,
                project=project
            )
            
            logging.info(f"Posted comment to PR {pr_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error posting PR comment: {str(e)}")
            return False
    
    async def create_work_item(
        self, 
        project: str, 
        title: str, 
        description: str
    ) -> Optional[int]:
        """Create a bug work item"""
        try:
            from azure.devops.v7_0.work_item_tracking.models import JsonPatchOperation
            
            document = [
                JsonPatchOperation(
                    op="add",
                    path="/fields/System.Title",
                    value=title
                ),
                JsonPatchOperation(
                    op="add",
                    path="/fields/System.Description",
                    value=description
                ),
                JsonPatchOperation(
                    op="add",
                    path="/fields/System.Tags",
                    value="AI-Generated; Pipeline-Failure"
                )
            ]
            
            try:
                work_item = self.work_item_client.create_work_item(
                    document=document,
                    project=project,
                    type="Bug"
                )
            except Exception as e:
                logging.warning(f"Could not create Bug, trying Task: {str(e)}")
                work_item = self.work_item_client.create_work_item(
                    document=document,
                    project=project,
                    type="Task"
                )
            
            logging.info(f"Created work item: {work_item.id}")
            return work_item.id
            
        except Exception as e:
            logging.error(f"Error creating work item: {str(e)}")
            return None