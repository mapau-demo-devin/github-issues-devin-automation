"""
Shared CLI utilities for GitHub Issues Devin Automation.
"""

import re
import click
import requests
from functools import wraps
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

def select_issue_interactively(github_client: GitHubClient, repo: str, state: str = 'open', labels: str = None, milestone: str = None, assignee: str = None) -> int:
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
    import inquirer
    
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
    
    issue_choices = []
    for issue in issues:
        title = issue['title']
        if len(title) > 60:
            title = title[:60] + "..."
        choice_text = f"#{issue['number']}: {title} (by {issue['user']['login']})"
        issue_choices.append((choice_text, issue['number']))
    
    try:
        console.print(f"\n[blue]Select an issue from {repo}[/blue]")
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
