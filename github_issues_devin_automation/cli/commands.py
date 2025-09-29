"""
CLI command definitions for GitHub Issues Devin Automation.
"""

import re
import click
import requests
import time
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner

from ..clients.github_client import GitHubClient
from .utils import (
    validate_repo_format, 
    validate_issue_number, 
    validate_repository_exists,
    handle_common_errors,
    _process_issue_with_devin,
    select_issue_interactively,
    console
)

def calculate_confidence_score_with_ai(issue, repo_info=None):
    """
    Calculate confidence score for issue implementation using Devin AI (1-10 scale).
    Higher score = higher confidence (easier to implement)
    """
    from ..clients.devin_client import DevinClient
    
    console.print(f"[blue]Creating Devin session to analyze issue complexity...[/blue]")
    
    scoping_prompt = f"""Please analyze this GitHub issue and provide a confidence score for implementation difficulty.

Issue Title: {issue.get('title', '')}
Issue Body: {issue.get('body', '') or 'No description provided'}
Labels: {', '.join([label.get('name', '') for label in issue.get('labels', [])])}

Please provide your analysis in this exact format:

CONFIDENCE SCORE: [number from 1-10]
CONFIDENCE LEVEL: [Very Low/Low/Medium/High/Very High]

ANALYSIS FACTORS:
- [Factor 1 explanation]
- [Factor 2 explanation]
- [Factor 3 explanation]

REASONING:
[Brief explanation of the score]

Note: 
- Score 1-2: Very complex, architectural changes, poorly defined
- Score 3-4: Complex, requires significant investigation
- Score 5-6: Moderate complexity, some unknowns
- Score 7-8: Well-defined, straightforward implementation
- Score 9-10: Simple fixes, documentation changes

Do NOT create any pull requests or implement solutions. This is only for scoping and analysis."""

    try:
        devin_client = DevinClient()
        
        session = devin_client.create_session(scoping_prompt)
        session_id = session['session_id']
        
        console.print(f"[green]Created scoping session: {session_id}[/green]")
        console.print(f"[dim]Session URL: {session['url']}[/dim]")
        
        completed_session = devin_client.wait_for_session_completion(session_id)
        
        score, factors, reasoning = _extract_confidence_from_session(completed_session)
        
        return score, factors, reasoning, session_id
        
    except Exception as e:
        console.print(f"[red]Error during AI analysis: {e}[/red]")
        console.print(f"[yellow]Falling back to rule-based scoring...[/yellow]")
        
        return calculate_confidence_score_fallback(issue, repo_info)

def calculate_confidence_score_fallback(issue, repo_info=None):
    """Fallback rule-based confidence scoring (original implementation)"""
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
    
    return round(score, 1), factors, "Rule-based analysis", None

def _extract_confidence_from_session(session):
    """Extract confidence score and analysis from completed Devin session"""
    messages = session.get('messages', [])
    
    for message in reversed(messages):
        if message.get('type') == 'devin_message':
            content = message.get('message', '')
            
            score = _parse_confidence_score(content)
            factors = _parse_analysis_factors(content)
            reasoning = _parse_reasoning(content)
            
            if score is not None:
                return score, factors, reasoning
    
    return 5.0, ["AI analysis completed but score parsing failed"], "Unable to parse Devin's response"

def _parse_confidence_score(content):
    """Parse confidence score from Devin's response"""
    score_match = re.search(r'CONFIDENCE SCORE:\s*(\d+(?:\.\d+)?)', content, re.IGNORECASE)
    if score_match:
        try:
            score = float(score_match.group(1))
            return max(1.0, min(10.0, score))
        except ValueError:
            pass
    
    return None

def _parse_analysis_factors(content):
    """Parse analysis factors from Devin's response"""
    factors = []
    
    factors_match = re.search(r'ANALYSIS FACTORS:(.*?)(?:REASONING:|$)', content, re.IGNORECASE | re.DOTALL)
    if factors_match:
        factors_text = factors_match.group(1)
        factor_lines = re.findall(r'-\s*(.+)', factors_text)
        factors = [factor.strip() for factor in factor_lines if factor.strip()]
    
    return factors if factors else ["AI analysis factors not parsed"]

def _parse_reasoning(content):
    """Parse reasoning from Devin's response"""
    reasoning_match = re.search(r'REASONING:\s*(.*?)$', content, re.IGNORECASE | re.DOTALL)
    if reasoning_match:
        return reasoning_match.group(1).strip()
    
    return "AI reasoning not parsed"

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
@click.option('--label', help='Filter by label names (comma-separated for multiple)')
@click.option('--milestone', help='Filter by milestone (number, "*" for any, "none" for none)')
@click.option('--assignee', help='Filter by assignee (username, "*" for any, "none" for unassigned)')
@handle_common_errors
def list_issues(repo, state, limit, label, milestone, assignee):
    """List GitHub issues from a repository"""
    github_client = GitHubClient()
    
    issues = github_client.list_issues(repo, state=state, limit=limit, labels=label, milestone=milestone, assignee=assignee)
    
    filter_info = []
    if label:
        filter_info.append(f"labels: {label}")
    if milestone:
        filter_info.append(f"milestone: {milestone}")
    if assignee:
        filter_info.append(f"assignee: {assignee}")
    
    title = f"Issues from {repo}"
    if filter_info:
        title += f" (filtered by {', '.join(filter_info)})"
    
    table = Table(title=title)
    table.add_column("Number", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("State", style="green")
    table.add_column("Author", style="yellow")
    table.add_column("Labels", style="magenta")
    table.add_column("Milestone", style="blue")
    table.add_column("Assignee", style="red")
    
    for issue in issues:
        labels_text = ', '.join([str(label['name']) for label in issue.get('labels', [])])
        milestone_text = str(issue.get('milestone', {}).get('title', '')) if issue.get('milestone') else ''
        assignee_text = str(issue.get('assignee', {}).get('login', '')) if issue.get('assignee') else ''
        
        table.add_row(
            str(issue['number']),
            str(issue['title'])[:50] + "..." if len(str(issue['title'])) > 50 else str(issue['title']),
            str(issue['state']),
            str(issue['user']['login']),
            labels_text[:20] + "..." if len(labels_text) > 20 else labels_text,
            milestone_text[:15] + "..." if len(milestone_text) > 15 else milestone_text,
            assignee_text
        )
    
    console.print(table)
    
    if github_client.has_many_issues(repo, threshold=limit, state=state, labels=label, milestone=milestone, assignee=assignee):
        console.print(f"\n[yellow]Note: Showing {limit} issues by default. You can view more issues by using the --limit argument.[/yellow]")

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--issue-number', type=int, help='Issue number to scope (optional - will prompt if not provided)')
@click.option('--label', help='Filter by label names (comma-separated for multiple)')
@click.option('--milestone', help='Filter by milestone (number, "*" for any, "none" for none)')
@click.option('--assignee', help='Filter by assignee (username, "*" for any, "none" for unassigned)')
def scope_issue(repo, issue_number, label, milestone, assignee):
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
            issue_number = select_issue_interactively(github_client, repo, labels=label, milestone=milestone, assignee=assignee)
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
        
        score, factors, reasoning, session_id = calculate_confidence_score_with_ai(issue)
        level, color, description = explain_confidence_score(score, factors)
        
        score_panel = Panel(
            f"[bold {color}]{level} Confidence ({score}/10)[/bold {color}]\n\n"
            f"{description}\n\n"
            f"[dim]AI Analysis:[/dim]\n{reasoning}\n\n"
            f"[dim]Key factors:[/dim]\n" + 
            "\n".join([f"• {factor}" for factor in factors]) +
            (f"\n\n[dim]Scoping session: {session_id}[/dim]" if session_id else ""),
            title="🎯 AI-Powered Confidence Score",
            border_style=color
        )
        console.print(score_panel)
        
        console.print(f"\n[yellow]Would you like to create a separate Devin session to implement this issue?[/yellow]")
        user_input = click.prompt("Create implementation session? (y/N)", default="n", show_default=True)
        
        if user_input.lower() in ['y', 'yes']:
            console.print(f"\n[blue]Creating implementation session for issue #{issue_number}...[/blue]")
            
            implementation_prompt = f"""Please implement a solution for this GitHub issue:

Issue: {issue['title']}
Description: {issue['body']}
Repository: {repo}

AI Confidence Analysis:
- Score: {score}/10 ({level})
- Key factors: {', '.join(factors[:3])}
- Reasoning: {reasoning}

Steps:
1. Clone the repository
2. Analyze the codebase
3. Implement the requested feature/fix
4. Create tests if appropriate
5. Create a pull request

Note: This is an implementation session. Please create a working solution and PR."""
            
            _process_issue_with_devin(
                repo, 
                issue_number, 
                implementation_prompt,
                score=score,
                level=level,
                ai_analysis=reasoning
            )
        else:
            console.print("[dim]Skipping implementation session creation.[/dim]")
        
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
@click.option('--issue-number', type=int, help='Issue number to complete (optional - will prompt if not provided)')
@click.option('--label', help='Filter by label names (comma-separated for multiple)')
@click.option('--milestone', help='Filter by milestone (number, "*" for any, "none" for none)')
@click.option('--assignee', help='Filter by assignee (username, "*" for any, "none" for unassigned)')
def complete_issue(repo, issue_number, label, milestone, assignee):
    """Complete an issue using Devin AI"""
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
            issue_number = select_issue_interactively(github_client, repo, labels=label, milestone=milestone, assignee=assignee)
        except click.ClickException as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    else:
        if not validate_issue_number(issue_number):
            console.print(f"[red]Error: Invalid issue number '{issue_number}'[/red]")
            console.print(f"[yellow]Issue numbers must be positive integers[/yellow]")
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
