"""
Shared CLI utilities for GitHub Issues Devin Automation.
"""

import re
import requests
import click
import inquirer
from functools import wraps
from typing import Optional, Dict, Any
from rich.console import Console
from ..clients.github_client import GitHubClient
from ..clients.devin_client import DevinClient

console = Console()

def validate_repo_format(repo: str) -> bool:
    """Validate repository format (owner/repo)"""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?/[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$'
    return bool(re.match(pattern, repo))

def validate_issue_number(issue_number: int) -> bool:
    """Validate issue number is positive"""
    return issue_number > 0

def validate_repository_exists(github_client: GitHubClient, repo: str) -> tuple[bool, str]:
    """Check if repository exists and is accessible"""
    try:
        github_client.get_repository(repo)
        return True, ""
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return False, f"Repository '{repo}' not found or not accessible"
        elif e.response.status_code == 403:
            return False, f"Access denied to repository '{repo}'. Check your GitHub token permissions"
        elif e.response.status_code == 401:
            return False, f"Authentication failed. Check your GITHUB_TOKEN environment variable"
        else:
            return False, f"Error accessing repository '{repo}': {e}"
    except Exception as e:
        return False, f"Error accessing repository '{repo}': {e}"

def handle_common_errors(func):
    """Decorator for common CLI error handling patterns"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                console.print(f"[red]Error: Issue not found[/red]")
                console.print(f"[yellow]Tip: Use 'list-issues' to see available issues[/yellow]")
            else:
                console.print(f"[red]HTTP Error: {e}[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    return wrapper

def _process_issue_with_devin(repo: str, issue_number: int, prompt_template: str, **session_kwargs) -> None:
    """Common logic for processing issues with Devin AI"""
    github_client = GitHubClient()
    devin_client = DevinClient()
    
    try:
        issue = github_client.get_issue(repo, issue_number)
        console.print(f"[blue]Processing issue #{issue_number}: {issue['title']}[/blue]")
        
        prompt = prompt_template.format(
            title=issue['title'],
            body=issue['body'],
            repo=repo,
            issue_number=issue_number,
            **session_kwargs
        )
        
        session = devin_client.create_session(prompt)
        console.print(f"[green]Created Devin session: {session['session_id']}[/green]")
        console.print(f"[blue]Session URL: {session['url']}[/blue]")
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error: Issue #{issue_number} not found in repository {repo}[/red]")
            console.print(f"[yellow]Tip: Use 'list-issues --repo {repo}' to see available issues[/yellow]")
        else:
            console.print(f"[red]HTTP Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error processing issue: {e}[/red]")

def select_issue_interactively(github_client: GitHubClient, repo: str, state: str = 'open', labels: Optional[str] = None, milestone: Optional[str] = None, assignee: Optional[str] = None) -> int:
    """
    Interactively select an issue from a repository using arrow keys.
    
    Args:
        github_client: GitHub client instance
        repo: Repository in format 'owner/repo'
        state: Issue state to filter by
        labels: Comma-separated list of label names to filter by
        milestone: Milestone number, title, "*" for any, "none" for none
        assignee: Username, "*" for any assigned, "none" for unassigned
    
    Returns:
        Selected issue number
    """
    try:
        if github_client.has_many_issues(repo, threshold=10, state=state, labels=labels, milestone=milestone, assignee=assignee):
            console.print(f"[yellow]This repository has more than 10 {state} issues.[/yellow]")
            while True:
                try:
                    limit = click.prompt("How many issues would you like to display?", type=int, default=20)
                    if limit > 0:
                        break
                    console.print("[red]Please enter a positive number.[/red]")
                except click.Abort:
                    raise click.ClickException("Operation cancelled")
        else:
            limit = 50
        
        issues = github_client.list_issues(repo, state=state, limit=limit, labels=labels, milestone=milestone, assignee=assignee)
    except ValueError as e:
        raise click.ClickException(str(e))
    
    if not issues:
        raise click.ClickException(f"No {state} issues found in repository {repo}")
    
    from .commands import create_issues_table
    filter_info = []
    if labels:
        filter_info.append(f"labels: {labels}")
    if milestone:
        filter_info.append(f"milestone: {milestone}")
    if assignee:
        filter_info.append(f"assignee: {assignee}")
    
    table = create_issues_table(issues, f"Issues from {repo}", filter_info if filter_info else None)
    console.print(table)
    
    issue_choices = []
    for issue in issues:
        title = str(issue['title'])
        if len(title) > 60:
            title = title[:60] + "..."
        choice_text = f"#{issue['number']}: {title} (by {issue['user']['login']})"
        issue_choices.append((choice_text, issue['number']))
    
    try:
        console.print(f"\n[blue]Select an issue from the table above[/blue]")
        console.print("[dim]Use arrow keys to navigate, Enter to select[/dim]\n")
        
        questions = [
            inquirer.List('issue',
                         message="Select an issue",
                         choices=issue_choices,
                         carousel=True)
        ]
        
        answers = inquirer.prompt(questions)
        if answers is None:
            raise click.ClickException("Operation cancelled")
        
        return answers['issue']
        
    except KeyboardInterrupt:
        raise click.ClickException("Operation cancelled")
