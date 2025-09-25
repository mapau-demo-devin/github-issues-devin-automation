# GitHub Issues Devin Automation

A CLI tool that integrates GitHub Issues with Devin AI to automate issue scoping and completion.

## Features

- **List Issues**: View GitHub issues from specified repositories
- **Scope Issues**: Trigger Devin sessions to analyze issues and assign confidence scores
- **Complete Issues**: Trigger Devin sessions to implement solutions based on action plans

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Run the CLI:
```bash
python cli.py --help
```

## Configuration

- `GITHUB_TOKEN`: GitHub personal access token
- `DEVIN_API_KEY`: Devin API key
- `DEVIN_API_BASE_URL`: Devin API base URL (default: https://api.devin.ai/v1)

## Usage

```bash
# List issues from a repository
python cli.py list-issues --repo owner/repo

# Scope an issue with Devin
python cli.py scope-issue --repo owner/repo --issue-number 123

# Complete an issue with Devin
python cli.py complete-issue --repo owner/repo --issue-number 123
```
