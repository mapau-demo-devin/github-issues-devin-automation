"""
CLI command definitions for GitHub Issues Devin Automation.
"""

import re
import click
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..clients.github_client import GitHubClient
from .utils import (
    validate_repo_format, 
    validate_issue_number, 
    validate_repository_exists,
    handle_common_errors,
    _process_issue_with_devin,
    console
)

def calculate_confidence_score(issue, repo_info=None):
    """
    Calculate confidence score for issue implementation (1-10 scale).
    Higher score = higher confidence (easier to implement)
    """
    score = 5.0
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

@click.group()
def cli():
    """GitHub Issues Devin Automation CLI"""
    pass

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--state', default='open', help='Issue state (open, closed, all)')
@click.option('--limit', default=10, help='Maximum number of issues to display')
@handle_common_errors
def list_issues(repo, state, limit):
    """List GitHub issues from a repository"""
    github_client = GitHubClient()
    
    issues = github_client.list_issues(repo, state=state, limit=limit)
    
    table = Table(title=f"Issues from {repo}")
    table.add_column("Number", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("State", style="green")
    table.add_column("Author", style="yellow")
    
    for issue in issues:
        table.add_row(
            str(issue['number']),
            issue['title'][:50] + "..." if len(issue['title']) > 50 else issue['title'],
            issue['state'],
            issue['user']['login']
        )
    
    console.print(table)

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--issue-number', required=True, type=int, help='Issue number to scope')
def scope_issue(repo, issue_number):
    """Analyze issue complexity and provide confidence score"""
    if not validate_repo_format(repo):
        console.print(f"[red]Error: Invalid repository format '{repo}'[/red]")
        console.print(f"[yellow]Expected format: owner/repo (e.g., 'mapau-demo-devin/running-buddy')[/yellow]")
        return
    
    if not validate_issue_number(issue_number):
        console.print(f"[red]Error: Invalid issue number '{issue_number}'[/red]")
        console.print(f"[yellow]Issue numbers must be positive integers[/yellow]")
        return
    
    github_client = GitHubClient()
    
    repo_exists, repo_error = validate_repository_exists(github_client, repo)
    if not repo_exists:
        console.print(f"[red]Error: {repo_error}[/red]")
        console.print(f"[yellow]Tip: Verify the repository name and your access permissions[/yellow]")
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
            
            prompt_template = """
            Please implement a solution for this GitHub issue:
            
            Issue: {title}
            Description: {body}
            Repository: {repo}
            
            Confidence Score: {score}/10 ({level})
            Key factors: {factors}
            
            Steps:
            1. Clone the repository
            2. Analyze the codebase
            3. Implement the requested feature/fix
            4. Create tests if appropriate
            5. Create a pull request
            """
            
            _process_issue_with_devin(
                repo, 
                issue_number, 
                prompt_template,
                score=score,
                level=level,
                factors=', '.join(factors[:3])
            )
        else:
            console.print("[dim]Skipping Devin session creation.[/dim]")
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error: Issue #{issue_number} not found in repository {repo}[/red]")
            console.print(f"[yellow]Tip: Use 'list-issues --repo {repo}' to see available issues[/yellow]")
        else:
            console.print(f"[red]HTTP Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error scoping issue: {e}[/red]")

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--issue-number', required=True, type=int, help='Issue number to complete')
def complete_issue(repo, issue_number):
    """Complete an issue using Devin AI"""
    if not validate_repo_format(repo):
        console.print(f"[red]Error: Invalid repository format '{repo}'[/red]")
        console.print(f"[yellow]Expected format: owner/repo (e.g., 'mapau-demo-devin/running-buddy')[/yellow]")
        return
    
    if not validate_issue_number(issue_number):
        console.print(f"[red]Error: Invalid issue number '{issue_number}'[/red]")
        console.print(f"[yellow]Issue numbers must be positive integers[/yellow]")
        return
    
    github_client = GitHubClient()
    
    repo_exists, repo_error = validate_repository_exists(github_client, repo)
    if not repo_exists:
        console.print(f"[red]Error: {repo_error}[/red]")
        console.print(f"[yellow]Tip: Verify the repository name and your access permissions[/yellow]")
        return
    
    prompt_template = """
    Please implement a solution for this GitHub issue:
    
    Issue: {title}
    Description: {body}
    Repository: {repo}
    
    Steps:
    1. Clone the repository
    2. Analyze the codebase
    3. Implement the requested feature/fix
    4. Create tests if appropriate
    5. Create a pull request
    """
    
    _process_issue_with_devin(repo, issue_number, prompt_template)
