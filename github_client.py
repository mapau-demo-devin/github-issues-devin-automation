"""
GitHub API client for fetching issues and repository information.
"""

import os
import requests
from typing import List, Dict, Any

class GitHubClient:
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def list_issues(self, repo: str, state: str = 'open', limit: int = 10, return_headers: bool = False, labels: str = None, milestone: str = None, assignee: str = None):
        """
        List issues from a GitHub repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            state: Issue state ('open', 'closed', 'all')
            limit: Maximum number of issues to return
            return_headers: If True, return (issues, headers) tuple
            labels: Comma-separated list of label names to filter by
            milestone: Milestone number, "*" for any, "none" for none
            assignee: Username, "*" for any assigned, "none" for unassigned
        
        Returns:
            List of issue dictionaries, or tuple of (issues, headers) if return_headers=True
        """
        url = f"{self.base_url}/repos/{repo}/issues"
        params = {
            'state': state,
            'per_page': limit,
            'sort': 'updated',
            'direction': 'desc'
        }
        
        if labels:
            params['labels'] = labels
        if milestone:
            params['milestone'] = milestone
        if assignee:
            params['assignee'] = assignee
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        if return_headers:
            return response.json(), dict(response.headers)
        return response.json()
    
    def get_issue(self, repo: str, issue_number: int) -> Dict[Any, Any]:
        """
        Get a specific issue from a GitHub repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            issue_number: Issue number
        
        Returns:
            Issue dictionary
        """
        url = f"{self.base_url}/repos/{repo}/issues/{issue_number}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def get_repository(self, repo: str) -> Dict[Any, Any]:
        """
        Get repository information.
        
        Args:
            repo: Repository in format 'owner/repo'
        
        Returns:
            Repository dictionary
        """
        url = f"{self.base_url}/repos/{repo}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def has_many_issues(self, repo: str, threshold: int = 10, state: str = 'open', labels: str = None, milestone: str = None, assignee: str = None) -> bool:
        """
        Check if repository has more than threshold number of issues.
        
        Args:
            repo: Repository in format 'owner/repo'
            threshold: Number to check against
            state: Issue state ('open', 'closed', 'all')
            labels: Comma-separated list of label names to filter by
            milestone: Milestone number, "*" for any, "none" for none
            assignee: Username, "*" for any assigned, "none" for unassigned
        
        Returns:
            True if repo has more than threshold issues
        """
        issues, headers = self.list_issues(repo, state=state, limit=threshold + 1, return_headers=True, labels=labels, milestone=milestone, assignee=assignee)
        return len(issues) > threshold or ('link' in headers and 'rel="next"' in headers['link'])
