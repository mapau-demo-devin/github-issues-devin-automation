# GitHub Issues Devin Automation

A CLI tool that integrates GitHub Issues with Devin AI to automate issue scoping and completion.

## Features

- **List Issues**: View GitHub issues from specified repositories
- **Scope Issues**: Trigger Devin sessions to analyze issues and assign confidence scores
- **Complete Issues**: Trigger Devin sessions to implement solutions based on action plans

## System Requirements

- Python 3.7+
- OpenSSL 1.1.1+ or compatible SSL library

**Note**: If you encounter urllib3 warnings about LibreSSL compatibility, the requirements.txt file pins urllib3 to v1.x to avoid this issue.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```
   **Note**: This includes the `questionary` library for interactive arrow key navigation.

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

### Required Environment Variables
- `GITHUB_TOKEN`: GitHub personal access token with repo access
- `DEVIN_API_KEY`: Devin API key for session creation

### Optional Environment Variables
- `DEVIN_API_BASE_URL`: Devin API base URL (default: `https://api.devin.ai/v1`)
- `DEVIN_API_TIMEOUT`: Request timeout in seconds (default: `120`)
- `DEVIN_API_MAX_RETRIES`: Maximum retry attempts for failed requests (default: `3`)

### Setting up API Keys

1. **GitHub Token**: Create a personal access token at https://github.com/settings/tokens with `repo` scope
2. **Devin API Key**: Obtain from your Devin AI account settings

```bash
# Example .env file
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEVIN_API_KEY=your_devin_api_key_here
DEVIN_API_BASE_URL=https://api.devin.ai/v1
DEVIN_API_TIMEOUT=120
DEVIN_API_MAX_RETRIES=3
```

## Usage

### List Issues
View open issues from any GitHub repository:

```bash
# List open issues (default)
python cli.py list-issues --repo microsoft/vscode

# List all issues (open and closed)
python cli.py list-issues --repo facebook/react --state all

# Limit number of results
python cli.py list-issues --repo nodejs/node --limit 5
```

### Scope Issues with AI Analysis
Get Devin AI to analyze issue complexity and provide estimates:

```bash
# Analyze a specific issue
python cli.py scope-issue --repo microsoft/vscode --issue-number 123

# Interactive issue selection (new!)
python cli.py scope-issue --repo microsoft/vscode
# Use arrow keys to navigate, Enter to select

# Example output:
# Scoping issue #123: Add dark mode support
# Created Devin session: devin-abc123...
# Session URL: https://app.devin.ai/sessions/abc123...
```

### Complete Issues with AI Implementation
Have Devin AI implement solutions for GitHub issues:

```bash
# Implement a solution for an issue
python cli.py complete-issue --repo your-org/your-repo --issue-number 456

# Interactive issue selection (new!)
python cli.py complete-issue --repo your-org/your-repo
# Use arrow keys to navigate, Enter to select

# Example output:
# Completing issue #456: Fix login validation bug
# Created Devin session: devin-def456...
# Session URL: https://app.devin.ai/sessions/def456...
```

## Workflow Examples

### 1. Triaging New Issues
```bash
# First, list recent issues
python cli.py list-issues --repo your-org/project --limit 10

# Scope high-priority issues for complexity analysis
python cli.py scope-issue --repo your-org/project --issue-number 42
python cli.py scope-issue --repo your-org/project --issue-number 43

# Review Devin's analysis in the provided session URLs
```

### 2. Automated Issue Resolution
```bash
# For well-defined bugs or features, trigger implementation
python cli.py complete-issue --repo your-org/project --issue-number 42

# Monitor the Devin session for:
# - Code analysis and understanding
# - Implementation planning
# - Pull request creation
# - Testing and validation
```

### 3. Batch Processing
```bash
# Process multiple issues efficiently
for issue in 101 102 103; do
  python cli.py scope-issue --repo your-org/project --issue-number $issue
  sleep 5  # Rate limiting
done
```

## Troubleshooting

### Common Issues

**Timeout Errors**: If you encounter 504 Gateway Timeout errors, increase the timeout:
```bash
export DEVIN_API_TIMEOUT=300  # 5 minutes
python cli.py scope-issue --repo owner/repo --issue-number 123
```

**Rate Limiting**: Add delays between requests for batch processing:
```bash
python cli.py scope-issue --repo owner/repo --issue-number 1
sleep 10
python cli.py scope-issue --repo owner/repo --issue-number 2
```

**Authentication Errors**: Verify your tokens have the correct permissions:
- GitHub token needs `repo` scope for private repositories
- Devin API key must be valid and active

**urllib3 SSL Warnings**: If you see warnings about urllib3 v2 and LibreSSL compatibility:
```
/path/to/python/lib/python3.x/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'
```
This is resolved by the urllib3 version constraint in requirements.txt. Reinstall dependencies:
```bash
pip install -r requirements.txt --force-reinstall
```
