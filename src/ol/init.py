"""Initialization module for ol."""

import os
from pathlib import Path
import shutil
import yaml
from .config import DEFAULT_CONFIG

DEFAULT_TEMPLATES = {
    'code_review.yaml': '''
name: Code Review
description: Template for code review with customizable focus areas
template: |
    Please review this {language} code with a focus on:
    
    1. Code Quality
       - Clean code principles
       - DRY (Don't Repeat Yourself)
       - SOLID principles
    
    2. Performance
       - Time complexity
       - Space complexity
       - Resource usage
    
    3. Security
       - Input validation
       - Error handling
       - Security best practices
    
    4. Best Practices
       - Language-specific conventions
       - Documentation
       - Testing considerations
    
    Code to review:
    {content}
    
    Please provide:
    1. Summary of findings
    2. Specific issues and recommendations
    3. Code examples for improvements
variables:
    language:
        description: Programming language of the code
        default: Python
    content:
        description: The code content to review
        required: true
''',
    
    'documentation.yaml': '''
name: Documentation Generator
description: Template for generating documentation
template: |
    Please generate comprehensive documentation for this {type} with a focus on:
    
    1. Overview
       - Purpose
       - Key features
       - Use cases
    
    2. Technical Details
       - Implementation
       - Dependencies
       - Requirements
    
    3. Usage Examples
       - Basic usage
       - Advanced scenarios
       - Common patterns
    
    Content to document:
    {content}
    
    Please provide:
    1. Clear and concise documentation
    2. Practical examples
    3. Best practices and recommendations
variables:
    type:
        description: Type of content to document (e.g., code, API, configuration)
        default: code
    content:
        description: The content to document
        required: true
''',
    
    'bug_analysis.yaml': '''
name: Bug Analysis
description: Template for analyzing and fixing bugs
template: |
    Please analyze this potential bug with the following structure:
    
    1. Bug Description
       - Symptoms
       - Expected behavior
       - Actual behavior
    
    2. Analysis
       - Root cause investigation
       - Impact assessment
       - Related components
    
    3. Solution
       - Proposed fixes
       - Implementation steps
       - Testing strategy
    
    Context:
    {context}
    
    Error/Issue:
    {error}
    
    Please provide:
    1. Detailed analysis
    2. Step-by-step solution
    3. Prevention recommendations
variables:
    context:
        description: Context where the bug occurs
        required: true
    error:
        description: Error message or unexpected behavior
        required: true
''',

    'compare_files.yaml': '''
name: File Comparison
description: Template for comparing multiple files
template: |
    Please compare these files with focus on:
    
    1. Content Analysis
       - Key differences
       - Shared elements
       - Pattern identification
    
    2. Quality Assessment
       - Code/content quality
       - Consistency
       - Best practices
    
    3. Recommendations
       - Improvements
       - Standardization
       - Refactoring opportunities
    
    File 1: {file1}
    
    File 2: {file2}
    
    Please provide:
    1. Comprehensive comparison
    2. Specific findings
    3. Actionable recommendations
variables:
    file1:
        description: Content of first file
        required: true
    file2:
        description: Content of second file
        required: true
'''
}

def ensure_config_dir() -> Path:
    """Create configuration directory if it doesn't exist."""
    config_dir = Path.home() / '.config' / 'ol'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def create_default_config(config_dir: Path) -> None:
    """Create default configuration file if it doesn't exist."""
    config_file = config_dir / 'config.yaml'
    if not config_file.exists():
        with open(config_file, 'w') as f:
            yaml.safe_dump(DEFAULT_CONFIG, f, default_flow_style=False)

def create_history_file(config_dir: Path) -> None:
    """Create command history file if it doesn't exist."""
    history_file = config_dir / 'history.yaml'
    if not history_file.exists():
        with open(history_file, 'w') as f:
            yaml.safe_dump({'commands': []}, f, default_flow_style=False)

def create_default_templates(templates_dir: Path) -> None:
    """Create default template files if they don't exist."""
    for filename, content in DEFAULT_TEMPLATES.items():
        template_file = templates_dir / filename
        if not template_file.exists():
            with open(template_file, 'w') as f:
                f.write(content.lstrip())

def initialize_ol() -> None:
    """Initialize ol configuration and directories."""
    config_dir = ensure_config_dir()
    create_default_config(config_dir)
    create_history_file(config_dir)
    
    # Create and populate templates directory
    templates_dir = config_dir / 'templates'
    templates_dir.mkdir(exist_ok=True)
    create_default_templates(templates_dir)
    
    # Create cache directory
    cache_dir = config_dir / 'cache'
    cache_dir.mkdir(exist_ok=True) 