#!/usr/bin/env python3
"""
GitHub Issues Devin Automation CLI

A command-line tool for integrating GitHub Issues with Devin AI.
"""

import os
import re
import click
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import inquirer

from github_client import GitHubClient
from devin_client import DevinClient

load_dotenv()
console = Console()

def validate_repo_format(repo: str) -> bool:
    """Validate repository format (owner/repo)"""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?/[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$'
    return bool(re.match(pattern, repo))

def validate_issue_number(issue_number: int) -> bool:
    """Validate issue number is positive
    
    Note: GitHub API has no separate endpoint to pre-validate issue numbers.
    This basic validation catches obvious invalid inputs before making API calls.
    """
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

@click.group()
def cli():
    """GitHub Issues Devin Automation CLI"""
    pass

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--state', default='open', help='Issue state (open, closed, all)')
@click.option('--limit', default=10, help='Maximum number of issues to display')
@click.option('--tag', help='Filter by label/tag (comma-separated for multiple)')
@click.option('--priority', help='Filter by priority label (high, medium, low)')
def list_issues(repo, state, limit, tag, priority):
    """List GitHub issues from a repository"""
    github_client = GitHubClient()
    
    try:
        labels = []
        if tag:
            labels.extend(tag.split(','))
        if priority:
            labels.append(priority)
        
        labels_param = ','.join(labels) if labels else None
        issues = github_client.list_issues(repo, state=state, limit=limit, labels=labels_param)
        
        filter_info = []
        if tag:
            filter_info.append(f"tags: {tag}")
        if priority:
            filter_info.append(f"priority: {priority}")
        
        title = f"Issues from {repo}"
        if filter_info:
            title += f" (filtered by {', '.join(filter_info)})"
        
        table = Table(title=title)
        table.add_column("Number", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("State", style="green")
        table.add_column("Author", style="yellow")
        table.add_column("Labels", style="magenta")
        
        for issue in issues:
            labels_text = ', '.join([label['name'] for label in issue.get('labels', [])])
            table.add_row(
                str(issue['number']),
                issue['title'][:50] + "..." if len(issue['title']) > 50 else issue['title'],
                issue['state'],
                issue['user']['login'],
                labels_text[:30] + "..." if len(labels_text) > 30 else labels_text
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error listing issues: {e}[/red]")

def select_issue_interactively(github_client: GitHubClient, repo: str, state: str = 'open') -> int:
    """
    Interactively select an issue from a repository using arrow keys.
    
    Args:
        github_client: GitHub client instance
        repo: Repository in format 'owner/repo'
        state: Issue state to filter by
    
    Returns:
        Selected issue number
    """
    if github_client.has_many_issues(repo, threshold=10, state=state):
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
    
    issues = github_client.list_issues(repo, state=state, limit=limit)
    
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

def calculate_confidence_score(issue, repo_info=None):
    """
    Calculate confidence score for issue implementation (1-10 scale).
    Higher score = higher confidence (easier to implement)
    """
    score = 5.0  # Base score
    factors = []
    
    title = issue.get('title', '').lower()
    body = issue.get('body', '') or ''
    body_lower = body.lower()
    
    if any(word in title for word in ['fix', 'bug', 'error', 'broken']):
        score += 1.5
        factors.append("Bug fix (typically well-defined)")
    elif any(word in title for word in ['add', 'implement', 'create']):
        score += 0.5
        factors.append("Feature addition")
    elif any(word in title for word in ['refactor', 'improve', 'optimize']):
        score -= 0.5
        factors.append("Refactoring (may require broader changes)")
    
    complex_keywords = ['architecture', 'design', 'framework', 'migration', 'breaking change']
    if any(keyword in title or keyword in body_lower for keyword in complex_keywords):
        score -= 2.0
        factors.append("Complex architectural changes detected")
    
    simple_keywords = ['typo', 'spelling', 'documentation', 'readme', 'comment']
    if any(keyword in title or keyword in body_lower for keyword in simple_keywords):
        score += 2.0
        factors.append("Simple documentation/text changes")
    
    if 'magic number' in title or 'constant' in title:
        score += 1.5
        factors.append("Code cleanup - extracting constants")
    
    if len(body) > 500:
        score += 1.0
        factors.append("Detailed description provided")
    elif len(body) < 100:
        score -= 1.0
        factors.append("Limited description - may need clarification")
    
    if '```' in body or 'code' in body_lower:
        score += 0.5
        factors.append("Code examples provided")
    
    if re.search(r'\d+\.|\-\s|\*\s', body):
        score += 0.5
        factors.append("Clear steps or requirements listed")
    
    labels = issue.get('labels', [])
    label_names = [label.get('name', '').lower() for label in labels]
    
    if 'good first issue' in label_names or 'beginner' in label_names:
        score += 1.5
        factors.append("Marked as beginner-friendly")
    elif 'help wanted' in label_names:
        score += 0.5
        factors.append("Community contribution welcome")
    
    if 'bug' in label_names:
        score += 1.0
        factors.append("Confirmed bug report")
    elif 'enhancement' in label_names:
        score += 0.5
        factors.append("Feature enhancement")
    
    score = max(1.0, min(10.0, score))
    
    return round(score, 1), factors

def explain_confidence_score(score, factors):
    """Generate explanation for the confidence score"""
    if score >= 8.0:
        level = "Very High"
        color = "bright_green"
        description = "This issue appears straightforward to implement with clear requirements."
    elif score >= 6.0:
        level = "High"
        color = "green"
        description = "This issue has good clarity and should be manageable to implement."
    elif score >= 4.0:
        level = "Medium"
        color = "yellow"
        description = "This issue may require some investigation or have moderate complexity."
    elif score >= 2.0:
        level = "Low"
        color = "orange"
        description = "This issue appears complex or lacks sufficient detail."
    else:
        level = "Very Low"
        color = "red"
        description = "This issue is likely very complex or poorly defined."
    
    return level, color, description

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--issue-number', type=int, help='Issue number to scope (optional - will prompt if not provided)')
def scope_issue(repo, issue_number):
    """Analyze issue complexity and provide confidence score"""
    if not validate_repo_format(repo):
        console.print(f"[red]Error: Invalid repository format '{repo}'[/red]")
        console.print(f"[yellow]Expected format: owner/repo (e.g., 'mapau-demo-devin/running-buddy')[/yellow]")
        return
    
    github_client = GitHubClient()
    
    repo_exists, repo_error = validate_repository_exists(github_client, repo)
    if not repo_exists:
        console.print(f"[red]Error: {repo_error}[/red]")
        console.print(f"[yellow]Tip: Verify the repository name and your access permissions[/yellow]")
        return
    
    if issue_number is None:
        try:
            issue_number = select_issue_interactively(github_client, repo)
        except click.ClickException as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    else:
        if not validate_issue_number(issue_number):
            console.print(f"[red]Error: Invalid issue number '{issue_number}'[/red]")
            console.print(f"[yellow]Issue numbers must be positive integers[/yellow]")
            return
    
    try:
        issue = github_client.get_issue(repo, issue_number)
        console.print(f"\n[blue]Analyzing issue #{issue_number}: {issue['title']}[/blue]")
        
        score, factors = calculate_confidence_score(issue)
        level, color, description = explain_confidence_score(score, factors)
        
        score_panel = Panel(
            f"[bold {color}]{level} Confidence ({score}/10)[/bold {color}]\n\n"
            f"{description}\n\n"
            f"[dim]Factors considered:[/dim]\n" + 
            "\n".join([f"• {factor}" for factor in factors]),
            title="🎯 Implementation Confidence Score",
            border_style=color
        )
        console.print(score_panel)
        
        console.print(f"\n[yellow]Would you like to create a Devin session to work on this issue?[/yellow]")
        user_input = click.prompt("Create Devin session? (y/N)", default="n", show_default=True)
        
        if user_input.lower() in ['y', 'yes']:
            console.print(f"\n[blue]Creating Devin session for issue #{issue_number}...[/blue]")
            
            devin_client = DevinClient()
            prompt = f"""
            Please implement a solution for this GitHub issue:
            
            Issue: {issue['title']}
            Description: {issue['body']}
            Repository: {repo}
            
            Confidence Score: {score}/10 ({level})
            Key factors: {', '.join(factors[:3])}
            
            Steps:
            1. Clone the repository
            2. Analyze the codebase
            3. Implement the requested feature/fix
            4. Create tests if appropriate
            5. Create a pull request
            """
            
            session = devin_client.create_session(prompt)
            console.print(f"[green]Created Devin session: {session['session_id']}[/green]")
            console.print(f"[blue]Session URL: {session['url']}[/blue]")
        else:
            console.print("[dim]Skipping Devin session creation.[/dim]")
        
    except requests.exceptions.HTTPError as e:
        # Note: After pre-flight repository validation passes, we assume 404 errors
        # from get_issue() indicate non-existent issues. However, edge cases exist:
        # - Different permissions (repo accessible but not specific issues)
        # - Timing issues (repo moved/renamed between repo check and issue check)
        # - API inconsistencies or temporary GitHub API issues
        # - Private issues visible only to certain users
        if e.response.status_code == 404:
            console.print(f"[red]Error: Issue #{issue_number} not found in repository {repo}[/red]")
            console.print(f"[yellow]Tip: Use 'list-issues --repo {repo}' to see available issues[/yellow]")
        else:
            console.print(f"[red]HTTP Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error scoping issue: {e}[/red]")

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--issue-number', type=int, help='Issue number to complete (optional - will prompt if not provided)')
def complete_issue(repo, issue_number):
    """Complete an issue using Devin AI"""
    if not validate_repo_format(repo):
        console.print(f"[red]Error: Invalid repository format '{repo}'[/red]")
        console.print(f"[yellow]Expected format: owner/repo (e.g., 'mapau-demo-devin/running-buddy')[/yellow]")
        return
    
    github_client = GitHubClient()
    devin_client = DevinClient()
    
    repo_exists, repo_error = validate_repository_exists(github_client, repo)
    if not repo_exists:
        console.print(f"[red]Error: {repo_error}[/red]")
        console.print(f"[yellow]Tip: Verify the repository name and your access permissions[/yellow]")
        return
    
    if issue_number is None:
        try:
            issue_number = select_issue_interactively(github_client, repo)
        except click.ClickException as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    else:
        if not validate_issue_number(issue_number):
            console.print(f"[red]Error: Invalid issue number '{issue_number}'[/red]")
            console.print(f"[yellow]Issue numbers must be positive integers[/yellow]")
            return
    
    try:
        issue = github_client.get_issue(repo, issue_number)
        console.print(f"[blue]Completing issue #{issue_number}: {issue['title']}[/blue]")
        
        prompt = f"""
        Please implement a solution for this GitHub issue:
        
        Issue: {issue['title']}
        Description: {issue['body']}
        Repository: {repo}
        
        Steps:
        1. Clone the repository
        2. Analyze the codebase
        3. Implement the requested feature/fix
        4. Create tests if appropriate
        5. Create a pull request
        """
        
        session = devin_client.create_session(prompt)
        console.print(f"[green]Created Devin session: {session['session_id']}[/green]")
        console.print(f"[blue]Session URL: {session['url']}[/blue]")
        
    except requests.exceptions.HTTPError as e:
        # Note: After pre-flight repository validation passes, we assume 404 errors
        # from get_issue() indicate non-existent issues. However, edge cases exist:
        # - Different permissions (repo accessible but not specific issues)
        # - Timing issues (repo moved/renamed between repo check and issue check)
        # - API inconsistencies or temporary GitHub API issues
        # - Private issues visible only to certain users
        if e.response.status_code == 404:
            console.print(f"[red]Error: Issue #{issue_number} not found in repository {repo}[/red]")
            console.print(f"[yellow]Tip: Use 'list-issues --repo {repo}' to see available issues[/yellow]")
        else:
            console.print(f"[red]HTTP Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error completing issue: {e}[/red]")

if __name__ == '__main__':
    cli()
