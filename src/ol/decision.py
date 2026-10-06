"""System One decision mode implementation."""

import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml
import requests
from .config import normalize_ollama_host


# Decision profile version 1 schema
PROFILE_VERSION = 1

# Question type limits per official API documentation
QUESTION_TYPE_LIMITS = {
    'noul': {'min': 2, 'max': 2},  # exactly 2 criteria (true/false)
    'choice': {'min': 2, 'max': 26},
    'score': {'min': 2, 'max': 26},
}


class DecisionError(Exception):
    """Base exception for decision mode errors."""
    pass


class ProfileError(DecisionError):
    """Profile validation or loading error."""
    pass


class CapabilityError(DecisionError):
    """Model capability error."""
    pass


def get_bundled_profiles_dir() -> Path:
    """Return the path to bundled decision profiles."""
    # Bundled profiles are in src/ol/decision_profiles/
    return Path(__file__).parent / 'decision_profiles'


def get_user_profiles_dir() -> Path:
    """Return the path to user decision profiles."""
    return Path.home() / '.config' / 'ol' / 'decisions'


def ensure_user_profiles_dir() -> Path:
    """Create user profiles directory if it doesn't exist."""
    user_dir = get_user_profiles_dir()
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def list_available_profiles() -> List[Tuple[str, str, Path]]:
    """
    List all available profiles (user + bundled).
    
    Returns:
        List of (name, description, path) tuples.
    """
    profiles = []
    
    # User profiles take precedence
    user_dir = get_user_profiles_dir()
    if user_dir.exists():
        for ext in ['yaml', 'yml', 'json']:
            for profile_file in user_dir.glob(f'*.{ext}'):
                name = profile_file.stem
                try:
                    profile = load_profile(name)
                    desc = profile.get('description', 'No description')
                    profiles.append((name, desc, profile_file))
                except Exception:
                    # Skip invalid profiles in listing
                    continue
    
    # Then bundled profiles (skip if name already exists)
    bundled_dir = get_bundled_profiles_dir()
    existing_names = {name for name, _, _ in profiles}
    if bundled_dir.exists():
        for ext in ['yaml', 'yml', 'json']:
            for profile_file in bundled_dir.glob(f'*.{ext}'):
                name = profile_file.stem
                if name not in existing_names:
                    try:
                        profile = load_profile(name)
                        desc = profile.get('description', 'No description')
                        profiles.append((name, desc, profile_file))
                    except Exception:
                        continue
    
    return sorted(profiles, key=lambda x: x[0])


def find_profile_path(name: str) -> Optional[Path]:
    """
    Find the path to a named profile.
    
    User profiles take precedence over bundled profiles.
    Returns None if not found.
    """
    # Check user profiles first
    user_dir = get_user_profiles_dir()
    for ext in ['yaml', 'yml', 'json']:
        user_path = user_dir / f'{name}.{ext}'
        if user_path.exists():
            return user_path
    
    # Check bundled profiles
    bundled_dir = get_bundled_profiles_dir()
    for ext in ['yaml', 'yml', 'json']:
        bundled_path = bundled_dir / f'{name}.{ext}'
        if bundled_path.exists():
            return bundled_path
    
    return None


def load_profile(name: str) -> Dict[str, Any]:
    """
    Load and validate a decision profile by name.
    
    Args:
        name: Profile name (without extension)
    
    Returns:
        Validated profile dictionary
    
    Raises:
        ProfileError: If profile not found or invalid
    """
    profile_path = find_profile_path(name)
    if profile_path is None:
        available = [n for n, _, _ in list_available_profiles()]
        suggestion = f" Did you mean: {available[0]}?" if available else ""
        raise ProfileError(f"Profile '{name}' not found.{suggestion}")
    
    # Load YAML or JSON
    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            if profile_path.suffix in ['.yaml', '.yml']:
                profile = yaml.safe_load(f)
            else:
                profile = json.load(f)
    except Exception as e:
        raise ProfileError(f"Failed to load profile '{name}': {e}")
    
    if not isinstance(profile, dict):
        raise ProfileError(f"Profile '{name}' must be a dictionary")
    
    # Validate profile
    validate_profile(profile, name)
    
    return profile


def validate_profile(profile: Dict[str, Any], name: str = 'unknown') -> None:
    """
    Validate a decision profile schema.
    
    Args:
        profile: Profile dictionary to validate
        name: Profile name for error messages
    
    Raises:
        ProfileError: If validation fails
    """
    # Check version
    version = profile.get('version')
    if version != PROFILE_VERSION:
        raise ProfileError(
            f"Profile '{name}' has unsupported version {version}, "
            f"expected {PROFILE_VERSION}"
        )
    
    # Check description
    if 'description' not in profile:
        raise ProfileError(f"Profile '{name}' missing required field 'description'")
    
    # Validate questions
    questions = profile.get('questions')
    if not questions or not isinstance(questions, dict):
        raise ProfileError(f"Profile '{name}' must have a 'questions' dictionary")
    
    if len(questions) < 1 or len(questions) > 64:
        raise ProfileError(
            f"Profile '{name}' must have 1-64 questions, got {len(questions)}"
        )
    
    # Validate each question
    for q_name, q_def in questions.items():
        if not isinstance(q_def, dict):
            raise ProfileError(
                f"Profile '{name}' question '{q_name}' must be a dictionary"
            )
        
        q_type = q_def.get('type')
        if q_type not in ['noul', 'choice', 'score']:
            raise ProfileError(
                f"Profile '{name}' question '{q_name}' has invalid type '{q_type}'"
            )
        
        # Validate criteria
        criteria = q_def.get('criteria', {})
        if not isinstance(criteria, dict):
            raise ProfileError(
                f"Profile '{name}' question '{q_name}' criteria must be a dictionary"
            )
        
        limits = QUESTION_TYPE_LIMITS[q_type]
        if len(criteria) < limits['min'] or len(criteria) > limits['max']:
            raise ProfileError(
                f"Profile '{name}' question '{q_name}' type '{q_type}' requires "
                f"{limits['min']}-{limits['max']} criteria, got {len(criteria)}"
            )
        
        # All criteria keys must be strings
        for key in criteria.keys():
            if not isinstance(key, str):
                raise ProfileError(
                    f"Profile '{name}' question '{q_name}' has non-string criteria key"
                )
    
    # Validate results if present
    results = profile.get('results', {})
    if results:
        for q_name, r_def in results.items():
            if q_name not in questions:
                raise ProfileError(
                    f"Profile '{name}' has results for unknown question '{q_name}'"
                )
            
            question = questions[q_name]
            q_type = question['type']
            
            if q_type == 'noul':
                # Validate noul thresholds
                if 'negative_below' not in r_def or 'positive_at_or_above' not in r_def:
                    raise ProfileError(
                        f"Profile '{name}' noul question '{q_name}' results must have "
                        "'negative_below' and 'positive_at_or_above'"
                    )
                
                neg_below = r_def['negative_below']
                pos_at_or_above = r_def['positive_at_or_above']
                
                if not (isinstance(neg_below, (int, float)) and 
                        isinstance(pos_at_or_above, (int, float))):
                    raise ProfileError(
                        f"Profile '{name}' noul question '{q_name}' thresholds must be numeric"
                    )
                
                if not (0 <= neg_below < pos_at_or_above <= 1):
                    raise ProfileError(
                        f"Profile '{name}' noul question '{q_name}' must satisfy "
                        f"0 <= negative_below < positive_at_or_above <= 1"
                    )
            
            elif q_type == 'choice':
                # Validate value_labels if present
                value_labels = r_def.get('value_labels', {})
                if value_labels:
                    criteria_keys = set(question['criteria'].keys())
                    for value, label in value_labels.items():
                        if value not in criteria_keys:
                            raise ProfileError(
                                f"Profile '{name}' choice question '{q_name}' has "
                                f"value_label for unknown choice '{value}'"
                            )
    
    # Validate input requirements if present
    input_reqs = profile.get('input', {})
    if input_reqs:
        if not isinstance(input_reqs, dict):
            raise ProfileError(f"Profile '{name}' 'input' must be a dictionary")


def check_model_capabilities(
    host: str,
    model: str,
    requires_vision: bool,
    debug: bool = False
) -> None:
    """
    Check if a model has required capabilities via /api/show.
    
    Args:
        host: Ollama host URL
        model: Model name
        requires_vision: Whether vision capability is required
        debug: Whether to show debug information
    
    Raises:
        CapabilityError: If model lacks required capabilities
    """
    host = normalize_ollama_host(host)
    api_url = f"{host}/api/show"
    
    if debug:
        print(f"Checking capabilities for model '{model}' at {host}", file=sys.stderr)
    
    try:
        response = requests.post(
            api_url,
            json={"name": model},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise CapabilityError(
            f"Could not verify model capabilities for '{model}' at {host}: {e}"
        )
    except (ValueError, TypeError) as e:
        raise CapabilityError(
            f"Invalid response from /api/show for model '{model}': {e}"
        )
    
    # Check for decision capability
    capabilities = data.get('capabilities', [])
    if not capabilities:
        raise CapabilityError(
            f"Model '{model}' at {host} does not report capabilities. "
            "System One decision mode requires Ollama 0.35.0 or later with "
            "decision-capable models."
        )
    
    if 'decision' not in capabilities:
        raise CapabilityError(
            f"Model '{model}' does not support System One decision mode. "
            "Use a decision-capable model (e.g., tev1, clef-flash)."
        )
    
    # Check for vision capability if images are present
    if requires_vision and 'vision' not in capabilities:
        raise CapabilityError(
            f"Model '{model}' does not support vision. "
            "Image decisions require a vision-capable decision model (e.g., clef-flash)."
        )
    
    if debug:
        print(f"Model '{model}' capabilities verified: {capabilities}", file=sys.stderr)


def make_decision_request(
    host: str,
    model: str,
    state: str,
    questions: Dict[str, Any],
    images: Optional[List[str]] = None,
    keep_alive: Optional[int] = None,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Make a System One decision request to Ollama.
    
    Args:
        host: Ollama host URL
        model: Model name
        state: State/context string
        questions: Questions dictionary
        images: Optional list of base64-encoded images
        keep_alive: Optional keep_alive value
        debug: Whether to show debug information
    
    Returns:
        Response dictionary from /v1/systemone
    
    Raises:
        DecisionError: If request fails
    """
    host = normalize_ollama_host(host)
    api_url = f"{host}/v1/systemone"
    
    payload = {
        "model": model,
        "state": state,
        "questions": questions,
    }
    
    if images:
        payload["images"] = images
    
    if keep_alive is not None:
        payload["keep_alive"] = keep_alive
    
    if debug:
        print("\n=== Decision API Request ===", file=sys.stderr)
        print(f"URL: {api_url}", file=sys.stderr)
        debug_payload = dict(payload)
        if images:
            debug_payload["images"] = f"[{len(images)} image(s)]"
        print(f"Payload: {json.dumps(debug_payload, indent=2)}", file=sys.stderr)
        print(file=sys.stderr)
    
    try:
        response = requests.post(
            api_url,
            json=payload,
            timeout=120,
        )
        
        # Check for specific error cases
        if response.status_code == 404:
            error_data = {}
            try:
                error_data = response.json()
            except Exception:
                pass
            
            error_msg = error_data.get('error', '')
            if 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower():
                raise DecisionError(
                    f"Model '{model}' not found on {host}. "
                    "Pull the model first: ollama pull " + model
                )
            else:
                raise DecisionError(
                    f"System One decision endpoint not available at {host}. "
                    "Requires Ollama 0.35.0 or later."
                )
        
        if response.status_code == 413:
            raise DecisionError(
                "Request too large. Reduce the number of images, "
                "questions, or state text and try again."
            )
        
        response.raise_for_status()
        data = response.json()
        
    except requests.exceptions.Timeout:
        raise DecisionError(
            f"Request timed out after 120 seconds. The model may be overloaded."
        )
    except requests.exceptions.RequestException as e:
        raise DecisionError(f"Decision request failed: {e}")
    except (ValueError, TypeError) as e:
        raise DecisionError(f"Invalid response from decision API: {e}")
    
    if debug:
        print("\n=== Decision API Response ===", file=sys.stderr)
        print(json.dumps(data, indent=2), file=sys.stderr)
        print(file=sys.stderr)
    
    # Validate response
    answers = data.get('answers', {})
    if not answers:
        raise DecisionError("Decision API returned no answers")
    
    return data


def interpret_noul_result(
    probability: float,
    thresholds: Dict[str, Any]
) -> Tuple[str, str]:
    """
    Interpret a noul probability using configured thresholds.
    
    Args:
        probability: Probability value (0-1)
        thresholds: Thresholds dictionary with negative_below, positive_at_or_above, and labels
    
    Returns:
        (category, label) tuple, e.g. ('negative', 'SFW')
    """
    neg_below = thresholds['negative_below']
    pos_at_or_above = thresholds['positive_at_or_above']
    labels = thresholds.get('labels', {})
    
    if probability < neg_below:
        category = 'negative'
    elif probability >= pos_at_or_above:
        category = 'positive'
    else:
        category = 'uncertain'
    
    label = labels.get(category, category.upper())
    return category, label


def format_decision_output(
    response: Dict[str, Any],
    profile: Dict[str, Any],
    source: str = '',
    json_output: bool = False
) -> str:
    """
    Format decision results for human or JSON output.
    
    Args:
        response: API response dictionary
        profile: Profile dictionary with results interpretation
        source: Source filename or description
        json_output: Whether to output JSON
    
    Returns:
        Formatted output string
    """
    answers = response['answers']
    questions = profile['questions']
    results_config = profile.get('results', {})
    
    if json_output:
        # JSON output format
        output = {
            'status': 'success',
            'model': response.get('model', ''),
            'source': source,
            'results': {},
            'raw_response': response
        }
        
        for q_name, answer in answers.items():
            question = questions[q_name]
            q_type = question['type']
            result_cfg = results_config.get(q_name, {})
            
            result = {'type': q_type, 'raw': answer}
            
            if q_type == 'noul':
                prob = answer.get('probability')
                if result_cfg:
                    category, label = interpret_noul_result(prob, result_cfg)
                    result['category'] = category
                    result['label'] = label
                    result['probability'] = prob
                else:
                    result['probability'] = prob
            
            elif q_type == 'choice':
                value = answer.get('choice') or answer.get('value')
                value_labels = result_cfg.get('value_labels', {})
                label = value_labels.get(value, value)
                result['value'] = value
                result['label'] = label
                result['probabilities'] = answer.get('probabilities', {})
                if 'confidence' in answer:
                    result['confidence'] = answer['confidence']
            
            elif q_type == 'score':
                result['value'] = answer.get('value')
            
            output['results'][q_name] = result
        
        return json.dumps(output, indent=2)
    
    else:
        # Human-readable output
        lines = []
        
        for q_name, answer in answers.items():
            question = questions[q_name]
            q_type = question['type']
            result_cfg = results_config.get(q_name, {})
            
            if q_type == 'noul':
                prob = answer.get('probability', 0)
                if result_cfg:
                    category, label = interpret_noul_result(prob, result_cfg)
                    output_line = f"{label}"
                    if source:
                        output_line += f"  {source}"
                    output_line += f"  p({label})={prob:.2f}"
                    lines.append(output_line)
                else:
                    output_line = f"p(true)={prob:.2f}"
                    if source:
                        output_line += f"  {source}"
                    lines.append(output_line)
            
            elif q_type == 'choice':
                value = answer.get('choice') or answer.get('value') or ''
                value_labels = result_cfg.get('value_labels', {})
                label = value_labels.get(value, value)
                
                if len(questions) > 1:
                    output_line = f"{q_name}: {label}"
                else:
                    output_line = str(label) if label is not None else ''
                
                if source:
                    output_line += f"  {source}"
                if 'confidence' in answer and answer['confidence'] is not None:
                    output_line += f"  conf={answer['confidence']:.2f}"
                lines.append(output_line)
                
                probabilities = answer.get('probabilities') or {}
                if probabilities:
                    sorted_probs = sorted(
                        probabilities.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )
                    prob_parts = [
                        f"{opt} {int(round(prob * 100))}%"
                        for opt, prob in sorted_probs
                    ]
                    lines.append(f"  {'  '.join(prob_parts)}")
            
            elif q_type == 'score':
                value = answer.get('value', 0)
                if len(questions) > 1:
                    output_line = f"{q_name}: {value:.2f}"
                else:
                    output_line = f"{value:.2f}"
                
                if source:
                    output_line += f"  {source}"
                lines.append(output_line)
        
        return '\n'.join(lines)


def create_inline_boolean_profile(question: str) -> Dict[str, Any]:
    """
    Create a temporary profile from an inline boolean question.
    
    Args:
        question: Question text (e.g., "Is this image blurry?")
    
    Returns:
        Profile dictionary
    """
    # Extract the question text and create boolean criteria
    return {
        'version': PROFILE_VERSION,
        'description': 'Temporary inline boolean question',
        'questions': {
            'answer': {
                'type': 'noul',
                'instructions': question,
                'criteria': {
                    'true': 'Yes',
                    'false': 'No'
                }
            }
        }
    }


def edit_profile(name: str, debug: bool = False) -> None:
    """
    Edit or create a user profile.
    
    Args:
        name: Profile name
        debug: Whether to show debug information
    
    Raises:
        SystemExit: If editor fails or validation fails after save
    """
    ensure_user_profiles_dir()
    user_path = get_user_profiles_dir() / f'{name}.yaml'
    
    # Check if profile exists (user or bundled)
    existing_path = find_profile_path(name)
    
    if existing_path and existing_path == user_path:
        # Edit existing user profile
        print(f"Editing existing profile: {user_path}")
    elif existing_path:
        # Copy bundled to user and edit
        print(f"Creating user copy of bundled profile: {name}")
        with open(existing_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(user_path, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        # Create new profile from template
        print(f"Creating new profile: {user_path}")
        template = {
            'version': PROFILE_VERSION,
            'description': 'TODO: Add profile description',
            'input': {
                'require_image': False  # or True for vision profiles
            },
            'state': 'TODO: Add default state/context (optional)',
            'questions': {
                'example_question': {
                    'type': 'noul',
                    'instructions': 'TODO: Add question instructions',
                    'criteria': {
                        'true': 'TODO: Define true condition',
                        'false': 'TODO: Define false condition'
                    }
                }
            },
            'results': {
                'example_question': {
                    'negative_below': 0.20,
                    'positive_at_or_above': 0.80,
                    'labels': {
                        'negative': 'NO',
                        'uncertain': 'REVIEW',
                        'positive': 'YES'
                    }
                }
            }
        }
        
        with open(user_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(template, f, default_flow_style=False, sort_keys=False)
    
    # Launch editor
    editor = os.environ.get('VISUAL') or os.environ.get('EDITOR') or 'vi'
    
    try:
        subprocess.run([editor, str(user_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Editor exited with code {e.returncode}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Editor '{editor}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Validate after save
    try:
        load_profile(name)
        print(f"Profile '{name}' validated successfully.")
    except ProfileError as e:
        print(f"Warning: Profile validation failed: {e}", file=sys.stderr)
        print(f"The profile was saved but may not work until fixed.", file=sys.stderr)
        sys.exit(1)
