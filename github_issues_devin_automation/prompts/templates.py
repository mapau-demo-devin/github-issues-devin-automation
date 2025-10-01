"""
Prompt templates for Devin AI sessions.
"""

COMPLETE_ISSUE_PROMPT = """
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

IMPLEMENTATION_PROMPT = """Please implement a solution for this GitHub issue:

Issue: {title}
Description: {body}
Repository: {repo}

AI Scoping Analysis:
- Confidence Level: {confidence_level}
- Analysis: {ai_analysis}

Steps:
1. Clone the repository
2. Analyze the codebase
3. Implement the requested feature/fix
4. Create tests if appropriate
5. Create a pull request

Note: This is an implementation session. Please create a working solution and PR."""

SCOPING_INITIAL_PROMPT = """Analyze this GitHub issue and provide a quick initial confidence assessment. Please update the structured output immediately when you assign a confidence score and brief_analysis. Use the following format for the structured_output:.
{{
  "confidence_level": "High|Medium|Low",
  "brief_analysis": "2-3 sentence analysis of scope and complexity"
}}

Issue Title: {title}
Issue Body: {body}
Labels: {labels}

**INSTRUCTIONS:**
1. Read the issue carefully
2. **AS SOON AS you determine your confidence level and scope, IMMEDIATELY update the structured output** with your confidence assessment and brief_analysis
3. Keep your analysis concise (2-3 sentences maximum)
4. Do NOT provide detailed analysis yet - just initial assessment
5. Do NOT create pull requests or implement solutions

**CRITICAL: Update the structured output immediately as soon as you have determined the confidence level and brief scope. Respond as fast as possible.**"""

SCOPING_DETAILED_PROMPT = """Now that you've provided the initial assessment, please provide a comprehensive detailed scope analysis using the following structured_output schema:
{{
  "detailed_analysis": "Comprehensive detailed scope analysis"
   "implementation_approach": "Detailed implementation approach"
  "testing_considerations": "Testing considerations"
}}

**INSTRUCTIONS FOR DETAILED ANALYSIS:**
1. Provide a comprehensive detailed scope assessment including:
   - Detailed implementation approach
   - Potential challenges and edge cases
   - Testing considerations
   - Files/components that need to be modified
   - Time breakdown by component
2. **UPDATE the structured output's detailed_scope_analysis field** when you complete the analysis
3. Do NOT create pull requests or implement solutions

**Take your time to be thorough and comprehensive.**"""
