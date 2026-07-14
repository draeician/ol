#!/usr/bin/env python3

import argparse
import base64
import json
import os
import subprocess
import sys
import shlex
import textwrap
import socket
import requests
import argcomplete
from argcomplete.completers import DirectoriesCompleter, FilesCompleter
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Dict
from urllib.parse import urlparse
import pypdf
from .config import Config

MODEL_TYPES = ('text', 'vision')

# Keep headroom for a reply so prompt-fit checks are not exactly at the
# context edge (which yields empty done_reason=length responses).
DEFAULT_REPLY_TOKEN_RESERVE = 512
# Conservative pad per image when vision tokens cannot be counted exactly.
DEFAULT_IMAGE_TOKEN_PAD = 768


def get_env() -> Dict[str, str]:
    """Get environment variables for Ollama."""
    env = os.environ.copy()
    if 'OLLAMA_HOST' in env:
        if env['OLLAMA_HOST'].startswith('http://') or env['OLLAMA_HOST'].startswith('https://'):
            return env
        # Add http:// prefix if not present
        env['OLLAMA_HOST'] = f"http://{env['OLLAMA_HOST']}"
    return env


def get_ollama_base_url(env: Optional[Dict[str, str]] = None) -> str:
    """Return the Ollama base URL from env or the local default."""
    if env and 'OLLAMA_HOST' in env:
        return env['OLLAMA_HOST'].rstrip('/')
    return 'http://localhost:11434'


def estimate_prompt_tokens(text: str) -> int:
    """
    Conservatively estimate token count without a tokenizer.

    Uses ~3 characters per token so we tend to over-count and fail safe
    when /api/tokenize is unavailable.
    """
    if not text:
        return 0
    return max(1, (len(text) + 2) // 3)


def count_prompt_tokens(
    base_url: str,
    model: str,
    prompt: str,
    debug: bool = False,
) -> tuple:
    """
    Count prompt tokens using Ollama /api/tokenize when available.

    Returns:
        tuple: (token_count, method) where method is "tokenize" or "estimate"
    """
    tokenize_url = f"{base_url.rstrip('/')}/api/tokenize"
    try:
        response = requests.post(
            tokenize_url,
            json={"model": model, "content": prompt},
            timeout=60,
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data.get('tokens'), list):
                count = len(data['tokens'])
                if debug:
                    print(f"Token count via /api/tokenize: {count}")
                return count, 'tokenize'
            for key in ('input_tokens', 'count', 'tokens'):
                if isinstance(data.get(key), int):
                    if debug:
                        print(f"Token count via /api/tokenize ({key}): {data[key]}")
                    return data[key], 'tokenize'
        elif debug:
            print(
                f"Tokenize unavailable ({response.status_code}); "
                f"using conservative estimate",
                file=sys.stderr,
            )
    except (requests.exceptions.RequestException, ValueError, TypeError) as e:
        if debug:
            print(
                f"Tokenize failed ({e}); using conservative estimate",
                file=sys.stderr,
            )

    count = estimate_prompt_tokens(prompt)
    if debug:
        print(f"Token count estimate: {count}")
    return count, 'estimate'


def get_effective_context_length(
    base_url: str,
    model: str,
    debug: bool = False,
) -> tuple:
    """
    Resolve the context window that will apply to this request.

    Prefer the currently loaded runner context from /api/ps (what actually
    fails in practice) over the model maximum from /api/show.

    Returns:
        tuple: (context_length, source_label)
    """
    base = base_url.rstrip('/')

    try:
        ps_resp = requests.get(f"{base}/api/ps", timeout=10)
        ps_resp.raise_for_status()
        for loaded in ps_resp.json().get('models') or []:
            name = loaded.get('name') or loaded.get('model') or ''
            if name != model:
                continue
            ctx = loaded.get('context_length')
            if isinstance(ctx, int) and ctx > 0:
                if debug:
                    print(f"Context from /api/ps (loaded): {ctx}")
                return ctx, 'currently loaded'
    except (requests.exceptions.RequestException, ValueError, TypeError) as e:
        if debug:
            print(f"Could not read /api/ps: {e}", file=sys.stderr)

    try:
        show_resp = requests.post(
            f"{base}/api/show",
            json={"name": model},
            timeout=30,
        )
        show_resp.raise_for_status()
        info = show_resp.json().get('model_info') or {}
        for key, value in info.items():
            if key.endswith('.context_length') and isinstance(value, int) and value > 0:
                if debug:
                    print(f"Context from /api/show ({key}): {value}")
                return value, 'model maximum'
    except (requests.exceptions.RequestException, ValueError, TypeError) as e:
        if debug:
            print(f"Could not read /api/show: {e}", file=sys.stderr)

    raise RuntimeError(
        f"Could not determine context window for model '{model}' at {base}"
    )


def ensure_prompt_fits_context(
    base_url: str,
    model: str,
    prompt: str,
    image_count: int = 0,
    reserve: int = DEFAULT_REPLY_TOKEN_RESERVE,
    debug: bool = False,
) -> None:
    """
    Hard-fail if the prompt cannot fit in the effective model context.

    Always runs (not debug-only). Exits with status 1 on failure so the
    problem cannot be ignored.
    """
    try:
        context_length, context_source = get_effective_context_length(
            base_url, model, debug=debug
        )
        prompt_tokens, method = count_prompt_tokens(
            base_url, model, prompt, debug=debug
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(
            f"Error: could not verify prompt size against model context: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    image_pad = max(0, image_count) * DEFAULT_IMAGE_TOKEN_PAD
    total_needed = prompt_tokens + image_pad + reserve
    available = context_length - reserve

    if debug:
        print("\n=== Context Check ===")
        print(f"Model: {model}")
        print(f"Host: {base_url}")
        print(f"Context window: {context_length} ({context_source})")
        print(f"Prompt tokens: {prompt_tokens} ({method})")
        if image_pad:
            print(f"Image token pad: {image_pad} ({image_count} image(s))")
        print(f"Reserved for reply: {reserve}")
        print(f"Total needed: {total_needed}")
        print()

    if total_needed > context_length:
        method_note = (
            "exact via /api/tokenize"
            if method == 'tokenize'
            else "conservative estimate (tokenize API unavailable)"
        )
        print(
            "Error: prompt is too large for the model context window.\n"
            f"  model: {model} @ {base_url}\n"
            f"  prompt tokens: {prompt_tokens} ({method_note})\n"
            f"  image pad: {image_pad}\n"
            f"  reserved for reply: {reserve}\n"
            f"  total needed: {total_needed}\n"
            f"  context window: {context_length} ({context_source})\n"
            f"  available for prompt+images: {max(0, available)}\n"
            "\n"
            "Refusing to send this request. The model would return an empty "
            "or truncated answer (done_reason=length). Shrink the input or "
            "raise the model's served context window.",
            file=sys.stderr,
        )
        sys.exit(1)

def get_hostname_for_filename(debug: bool = False) -> str:
    """
    Get the hostname to use in filenames.
    
    Extracts hostname from OLLAMA_HOST if set, otherwise uses local hostname.
    
    Args:
        debug: Whether to show debug information
    
    Returns:
        str: Hostname to use in filename
    """
    env = get_env()
    if 'OLLAMA_HOST' in env:
        try:
            # Parse the URL to extract hostname
            parsed = urlparse(env['OLLAMA_HOST'])
            hostname = parsed.hostname
            if hostname:
                return hostname
        except Exception as e:
            # If parsing fails, fall back to local hostname
            if debug:
                import traceback
                print(f"Warning: Failed to parse OLLAMA_HOST URL '{env['OLLAMA_HOST']}': {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
            else:
                print(f"Warning: Failed to parse OLLAMA_HOST URL, using local hostname", file=sys.stderr)
    # Fall back to local hostname
    return socket.gethostname()

def list_installed_models(env: Dict[str, str], debug: bool = False) -> List[str]:
    """
    Return a list of model names installed on the pointed Ollama host.
    
    Prefer JSON if available; otherwise parse tabular output.
    
    Args:
        env: Environment variables dict (from get_env())
        debug: Whether to show debug information
    
    Returns:
        List of model names
    """
    # Try JSON first (newer Ollama)
    try:
        r = subprocess.run(
            ['ollama', 'list', '--json'],
            env=env, capture_output=True, text=True, check=True
        )
        items = json.loads(r.stdout)
        # Accept either {"models":[{"name":...}, ...]} or a flat list of {"name":...}
        if isinstance(items, dict) and 'models' in items:
            items = items['models']
        names = [it['name'] for it in items if 'name' in it]
        if names:
            if debug:
                print(f"DEBUG: Found {len(names)} models via JSON", file=sys.stderr)
            return names
    except Exception as e:
        if debug:
            import traceback
            print(f"DEBUG: JSON parsing failed: {e}, falling back to text parsing", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        else:
            print(f"Warning: Failed to parse JSON model list, falling back to text parsing", file=sys.stderr)
    
    # Fallback: parse plain text table (header "NAME  ID  SIZE  MODIFIED")
    r = subprocess.run(
        ['ollama', 'list'],
        env=env, capture_output=True, text=True, check=True
    )
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    # Drop header if present
    if lines and lines[0].lower().startswith('name'):
        lines = lines[1:]
    names = [ln.split()[0] for ln in lines if ln and not ln.lower().startswith('name')]
    if debug:
        print(f"DEBUG: Found {len(names)} models via text parsing", file=sys.stderr)
    return names


def complete_model_type(prefix: str, **kwargs) -> List[str]:
    """Complete model type choices (text or vision)."""
    return [t for t in MODEL_TYPES if t.startswith(prefix)]


def complete_model_name(prefix: str, **kwargs) -> List[str]:
    """Complete installed Ollama model names matching prefix."""
    try:
        names = list_installed_models(get_env())
    except Exception:
        return []
    return [name for name in names if name.startswith(prefix)]


def complete_model_type_then_model(prefix: str, **kwargs) -> List[str]:
    """Complete type then model for --set-default-model (nargs=2)."""
    matches: List[str] = complete_model_type(prefix, **kwargs)
    for name in complete_model_name(prefix, **kwargs):
        if name not in matches:
            matches.append(name)
    return matches

def list_models() -> None:
    """List all available Ollama models."""
    try:
        subprocess.run(['ollama', 'list'], env=get_env(), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error listing models: {e}", file=sys.stderr)
        sys.exit(1)

def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary by reading its first few bytes."""
    try:
        with open(file_path, 'rb') as f:
            # Try to decode first few bytes as text
            chunk = f.read(1024)
            try:
                chunk.decode('utf-8')
                return False
            except UnicodeDecodeError:
                return True
    except IOError:
        return False

def is_image_file(file_path: str) -> bool:
    """Check if the file is an image."""
    supported_image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    unsupported_image_extensions = {'.webp', '.tiff', '.svg'}  # Can be expanded as needed
    ext = Path(file_path).suffix.lower()
    
    if ext in unsupported_image_extensions:
        print(f"Error: {ext} image format is not currently supported by Ollama. Please convert the image to a supported format ({', '.join(sorted(supported_image_extensions))}).", file=sys.stderr)
        sys.exit(1)
    
    return ext in supported_image_extensions

def get_file_type_and_prompt(file_path: str, config: Config) -> tuple[str, str]:
    """
    Determine the file type and get appropriate prompt and model.
    
    Returns:
        tuple: (model_type, prompt)
    """
    if is_image_file(file_path):
        return 'vision', config.get_default_prompt(file_path) or "What do you see in this image?"
    return 'text', config.get_default_prompt(file_path) or f"Please analyze this file: {file_path}"

def format_shell_command(cmd: List[str], input_str: Optional[str] = None, env_vars: Optional[Dict[str, str]] = None) -> str:
    """
    Format a command and its input for shell execution.
    
    Args:
        cmd: Command and arguments as list
        input_str: Optional input string to be passed to the command
        env_vars: Optional environment variables to be set
    
    Returns:
        str: Formatted shell command
    """
    # Build environment variables part
    env_part = ""
    if env_vars:
        env_part = "export " + " ".join(f"{k}={shlex.quote(v)}" for k, v in env_vars.items() if k != 'PATH') + " && "
    
    # Quote and escape the command and arguments
    quoted_cmd = ' '.join(shlex.quote(arg) for arg in cmd)
    
    if input_str:
        # Quote and escape the input string
        quoted_input = shlex.quote(input_str)
        # Create a shell-compatible echo command
        return f"{env_part}echo {quoted_input} | {quoted_cmd}"
    
    return f"{env_part}{quoted_cmd}"

def encode_image(file_path: str) -> str:
    """
    Read and base64 encode an image file.
    
    Args:
        file_path: Path to the image file
    
    Returns:
        str: Base64 encoded image content
    """
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def format_vision_prompt(prompt: str, image_data: str) -> str:
    """
    Format a prompt with image data for vision models.
    
    Args:
        prompt: The text prompt
        image_data: Base64 encoded image data
    
    Returns:
        str: Formatted prompt with image data
    """
    return f'{{"prompt": "{prompt}", "images": ["{image_data}"]}}'

def sanitize_model_name(model: str) -> str:
    """
    Sanitize a model name for use in filenames.
    
    Replaces path-hostile characters with safe alternatives.
    
    Args:
        model: The model name to sanitize
    
    Returns:
        Sanitized model name safe for filesystem use
    """
    # Replace path separators and other problematic characters
    safe = model.replace(':', '_')
    safe = safe.replace('/', '_')
    safe = safe.replace('\\', '_')
    safe = safe.replace(' ', '_')
    # Remove or replace other potentially problematic characters
    safe = safe.replace('|', '_')
    safe = safe.replace('<', '_')
    safe = safe.replace('>', '_')
    safe = safe.replace('"', '_')
    safe = safe.replace('*', '_')
    safe = safe.replace('?', '_')
    # Remove leading/trailing dots and spaces
    safe = safe.strip('. ')
    # Collapse multiple underscores
    while '__' in safe:
        safe = safe.replace('__', '_')
    return safe

def save_all_modelfiles(out_dir: Optional[str] = None, debug: bool = False) -> List[Path]:
    """
    Download and save Modelfiles for all installed models.
    
    Args:
        out_dir: Output directory (default: current working directory)
        debug: Whether to show debug information
    
    Returns:
        List of Paths to saved Modelfiles
    
    Raises:
        SystemExit: If model enumeration fails or any save fails
    """
    env = get_env()
    try:
        models = list_installed_models(env, debug)
        if not models:
            print("No models found on the Ollama host", file=sys.stderr)
            sys.exit(1)
        
        if debug:
            print(f"Found {len(models)} models to save", file=sys.stderr)
        
        saved_paths = []
        failed_models = []
        for model in models:
            try:
                path = save_modelfile(model, out_dir, debug)
                saved_paths.append(path)
            except (SystemExit, FileNotFoundError, OSError) as e:
                # If one model fails, continue with others but note the error
                error_msg = str(e) if hasattr(e, '__str__') else type(e).__name__
                print(f"Warning: Failed to save Modelfile for {model}: {error_msg}", file=sys.stderr)
                failed_models.append(model)
                continue
        
        if failed_models and not debug:
            print(f"Note: {len(failed_models)} model(s) failed to save. Use -d for details.", file=sys.stderr)
        
        return saved_paths
    except subprocess.CalledProcessError as e:
        error_msg = f"Error listing models (returncode {e.returncode})"
        if e.stderr:
            error_msg += f": {e.stderr.strip()}"
        print(error_msg, file=sys.stderr)
        sys.exit(1)

def save_modelfile(model: str, out_dir: Optional[str] = None, debug: bool = False) -> Path:
    """
    Download and save a model's Modelfile.
    
    Args:
        model: The model name (required)
        out_dir: Output directory (default: current working directory)
        debug: Whether to show debug information
    
    Returns:
        Path: The absolute path to the saved Modelfile
    
    Raises:
        SystemExit: If model is missing or subprocess fails
    """
    if not model:
        print("Error: --model is required when using --save-modelfile", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Call ollama show --modelfile
        result = subprocess.run(
            ['ollama', 'show', '--modelfile', model],
            capture_output=True,
            text=True,
            env=get_env(),
            check=True
        )
        
        # Build safe filename
        safe_model = sanitize_model_name(model)
        hostname = get_hostname_for_filename(debug=debug)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"{safe_model}-{hostname}-{timestamp}.modelfile"
        
        # Determine output directory
        if out_dir:
            output_path = Path(out_dir).expanduser().resolve()
        else:
            output_path = Path.cwd()
        
        # Create directory if needed
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Write file
        file_path = output_path / filename
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
        except (FileNotFoundError, OSError) as e:
            error_msg = f"Error writing Modelfile for {model}: {e}"
            print(error_msg, file=sys.stderr)
            sys.exit(1)
        
        # Print absolute path
        abs_path = file_path.resolve()
        print(str(abs_path))
        
        if debug:
            print(f"Saved Modelfile to {abs_path}", file=sys.stderr)
        
        return abs_path
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Error fetching Modelfile (returncode {e.returncode})"
        if e.stderr:
            error_msg += f": {e.stderr.strip()}"
        print(error_msg, file=sys.stderr)
        sys.exit(1)

def call_ollama_api(model: str, prompt: str, temperature: float, image_files: Optional[List[str]] = None, 
                    text_files: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None, 
                    debug: bool = False) -> None:
    """
    Call Ollama API with the given parameters.
    
    Routes image requests to /api/chat, text-only requests to /api/generate.
    
    Args:
        model: The model to use
        prompt: The prompt to send
        temperature: Temperature parameter (0.0-2.0)
        image_files: Optional list of image file paths
        text_files: Optional list of text file paths
        env: Environment variables dict
        debug: Whether to show debug information
    """
    base_url = get_ollama_base_url(env)
    
    # Route to /api/chat if images are present, otherwise use /api/generate
    has_images = image_files and len(image_files) > 0
    image_count = len(image_files) if image_files else 0

    # Always-on failsafe: refuse requests that cannot fit the effective context.
    ensure_prompt_fits_context(
        base_url,
        model,
        prompt,
        image_count=image_count,
        debug=debug,
    )
    
    if has_images:
        # Use /api/chat for image requests
        api_url = f"{base_url}/api/chat"
        
        # Build images array
        images = []
        for img_file in image_files:
            with open(img_file, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
                images.append(img_data)
        
        # Chat API uses messages array format
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": images
                }
            ],
            "temperature": temperature,
            "stream": True
        }
    else:
        # Use /api/generate for text-only requests
        api_url = f"{base_url}/api/generate"
        
        # Prompt is already complete (includes text file contents from run_ollama)
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": True
        }
        # Ensure images field is NOT included for text-only requests
        if 'images' in payload:
            del payload['images']
    
    if debug:
        print("\n=== API Request ===")
        print(f"URL: {api_url}")
        if has_images:
            print(f"Endpoint: /api/chat (images present)")
            # Create a simplified payload for debug output (hide image data)
            debug_payload = {}
            for k, v in payload.items():
                if k == 'messages':
                    debug_payload[k] = [
                        {
                            'role': m['role'],
                            'content': m['content'],
                            'images': f'[{len(m.get("images", []))} image(s)]'
                        }
                        for m in v
                    ]
                else:
                    debug_payload[k] = v
            print(f"Payload (without images): {json.dumps(debug_payload, indent=2)}")
        else:
            print(f"Endpoint: /api/generate (text-only)")
            print(f"Payload: {json.dumps(payload, indent=2)}")
        if image_files:
            print(f"Images: {len(image_files)} image(s) included")
        print()
    
    try:
        # Make streaming request
        response = requests.post(api_url, json=payload, stream=True, timeout=None)
        response.raise_for_status()
        
        # Stream and print response
        emitted_any = False
        done_reason = None
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    # Handle both /api/generate and /api/chat response formats
                    if 'response' in data:
                        # /api/generate format
                        chunk = data['response']
                        if chunk:
                            emitted_any = True
                        print(chunk, end='', flush=True)
                    elif (
                        'message' in data
                        and isinstance(data['message'], dict)
                        and 'content' in data['message']
                    ):
                        # /api/chat format
                        chunk = data['message']['content']
                        if chunk:
                            emitted_any = True
                        print(chunk, end='', flush=True)
                    if data.get('done', False):
                        done_reason = data.get('done_reason')
                        break
                except json.JSONDecodeError as e:
                    if debug:
                        print(f"Warning: Failed to parse JSON line in stream: {line.decode('utf-8', errors='replace')[:100]}", file=sys.stderr)
                        print(f"Error: {e}", file=sys.stderr)
                    # Continue processing other lines
                    continue
        
        print()  # Newline after response

        # Fail closed if Ollama truncated: empty or partial output from length limit.
        if done_reason == 'length':
            if emitted_any:
                print(
                    "\nError: model output was truncated (done_reason=length).\n"
                    "The response above may be incomplete or compromised. "
                    "Reduce input size or increase the model's context window.",
                    file=sys.stderr,
                )
            else:
                print(
                    "\nError: model returned no content (done_reason=length).\n"
                    "The prompt likely filled the entire context window, so no "
                    "reply tokens remained. Reduce input size or increase the "
                    "model's served context window.",
                    file=sys.stderr,
                )
            sys.exit(1)
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}", file=sys.stderr)
        sys.exit(1)

def run_ollama(prompt: str, model: str = None, files: Optional[List[str]] = None, 
               temperature: Optional[float] = None, debug: bool = False, 
               cli_host_provided: bool = False) -> None:
    """
    Run Ollama with the given prompt and optional files.
    
    Args:
        prompt: The prompt to send to Ollama
        model: The model to use (if None, will be determined from config)
        files: Optional list of files to inject into the prompt
        temperature: Temperature to use (if None, will use default from config)
        debug: Whether to show debug information
    """
    config = Config()
    
    # Process files first to determine their types (needed to determine model type)
    image_files = []
    text_files = []
    pdf_files = []
    
    if files:
        for file_path in files:
            # Convert to absolute path and expand user directory
            abs_path = os.path.abspath(os.path.expanduser(file_path))
            if not os.path.exists(abs_path):
                print(f"Error: File not found: {file_path}", file=sys.stderr)
                sys.exit(1)
            
            if is_image_file(abs_path):
                image_files.append(abs_path)
                if debug:
                    print(f"Added image file: {file_path} ({abs_path})")
            elif abs_path.lower().endswith('.pdf'):
                pdf_files.append(abs_path)
                if debug:
                    print(f"Added PDF file: {file_path} ({abs_path})")
            elif is_binary_file(abs_path):
                print(f"Warning: Skipping binary file: {file_path}", file=sys.stderr)
            else:
                text_files.append(abs_path)
                if debug:
                    print(f"Added text file: {file_path} ({abs_path})")
    
    # Determine the model to use and model type
    model_type = 'text'  # default
    if model is None:
        # Clear any previous last_used model to ensure clean selection
        config.set_last_used_model(None)
        
        if image_files and not text_files and not pdf_files:
            # Only use vision model if we have only image files
            model_type = 'vision'
            model = config.get_model_for_type('vision')
            if debug:
                print(f"Selected vision model for image files: {model}")
        else:
            # For text files or mixed content, always use text model
            model_type = 'text'
            model = config.get_model_for_type('text')
            if debug:
                print(f"Selected text model: {model}")
    else:
        # If model is provided, determine type based on files
        if image_files and not text_files and not pdf_files:
            model_type = 'vision'
        else:
            model_type = 'text'
    
    # Check if model type has a configured host, and use it if no CLI flags were provided
    # This must happen BEFORE get_env() is called
    if not cli_host_provided:
        config_host = config.get_host_for_type(model_type)
        if config_host:
            # Set OLLAMA_HOST from config (will be used by get_env() later)
            os.environ['OLLAMA_HOST'] = config_host
            if debug:
                print(f"Using configured host for {model_type} model: {config_host}")
    
    # Now get the environment (which will include the config host if set)
    env = get_env()
    is_remote = 'OLLAMA_HOST' in env
    
    # Determine temperature to use
    if temperature is None:
        temperature = config.get_temperature_for_type(model_type)
    else:
        # Validate provided temperature
        if not (0.0 <= temperature <= 2.0):
            print(f"Error: Temperature must be between 0.0 and 2.0, got {temperature}", file=sys.stderr)
            sys.exit(1)
    
    if debug:
        print("\n=== Debug Information ===")
        print(f"Model: {model}")
        print(f"Model Type: {model_type}")
        print(f"Temperature: {temperature}")
        print(f"Base Prompt: {prompt}")
        print(f"Files to process: {files if files else 'None'}")
        if is_remote:
            print(f"Ollama Host: {env['OLLAMA_HOST']}")
        print()

    # Build the complete prompt
    complete_prompt = prompt

    # Add text file contents to prompt
    for file_path in text_files:
        try:
            with open(file_path, 'r') as f:
                file_content = f.read()
                complete_prompt += f"\n\nContent of {os.path.basename(file_path)}:\n{file_content}"
                if debug:
                    print(f"Added content from {os.path.basename(file_path)}")
                    print(f"File content length: {len(file_content)} characters")
        except IOError as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)
            sys.exit(1)

    # Add PDF file contents to prompt (extract text via pypdf)
    for file_path in pdf_files:
        try:
            reader = pypdf.PdfReader(file_path)
            parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
            extracted_text = "\n".join(parts).strip()
            if not extracted_text:
                print(
                    f"Warning: No text extracted from PDF (may be scanned/image-only): {file_path}",
                    file=sys.stderr,
                )
                continue
            complete_prompt += (
                f"\n\nContent of {os.path.basename(file_path)}:\n{extracted_text}"
            )
            if debug:
                print(f"Added content from {os.path.basename(file_path)}")
                print(f"PDF content length: {len(extracted_text)} characters")
        except Exception as e:
            msg = str(e).lower()
            if "encrypted" in msg or "password" in msg:
                print(
                    f"Warning: Skipping encrypted PDF: {file_path}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Warning: Could not extract text from PDF {file_path}: {e}",
                    file=sys.stderr,
                )
            continue

    if debug:
        print("\n=== API Information ===")
        print(f"Will call Ollama API with:")
        print(f"  Model: {model}")
        print(f"  Temperature: {temperature}")
        print(f"  Prompt length: {len(complete_prompt)} characters")
        if image_files:
            print(f"  Images: {len(image_files)} image(s)")
        if text_files:
            print(f"  Text files: {len(text_files)} file(s)")
        if pdf_files:
            print(f"  PDF files: {len(pdf_files)} file(s)")
        print()

    try:
        # Use API instead of subprocess
        call_ollama_api(model, complete_prompt, temperature, image_files, text_files, env, debug)
        
        # Only save last used model after successful execution
        config.set_last_used_model(model)
    except Exception as e:
        print(f"Error running Ollama: {e}", file=sys.stderr)
        sys.exit(1)

def display_defaults(config: Config, env: Dict[str, str]) -> None:
    """
    Display current configuration defaults.
    
    Args:
        config: Config instance to retrieve model defaults
        env: Environment variables dict (from get_env())
    """
    # Determine host display
    if 'OLLAMA_HOST' in env:
        host = env['OLLAMA_HOST']
    else:
        host = 'localhost:11434'
    
    # Get model defaults
    text_model = config.get_model_for_type('text')
    vision_model = config.get_model_for_type('vision')
    last_used = config.get_last_used_model()
    
    # Get temperature defaults
    text_temp = config.get_temperature_for_type('text')
    vision_temp = config.get_temperature_for_type('vision')
    
    # Get host defaults
    text_host = config.get_host_for_type('text')
    vision_host = config.get_host_for_type('vision')
    
    # Format and print
    print("Current Configuration:")
    print(f"  Host: {host}")
    if text_host:
        print(f"  Default Text Host: {text_host}")
    else:
        print(f"  Default Text Host: localhost:11434 (default)")
    if vision_host:
        print(f"  Default Vision Host: {vision_host}")
    else:
        print(f"  Default Vision Host: localhost:11434 (default)")
    print(f"  Default Text Model: {text_model}")
    print(f"  Default Vision Model: {vision_model}")
    print(f"  Default Text Temperature: {text_temp}")
    print(f"  Default Vision Temperature: {vision_temp}")
    if last_used:
        print(f"  Last Used Model: {last_used}")
    else:
        print(f"  Last Used Model: None")

def set_default_model(config: Config, model_type: str, model_name: str) -> None:
    """
    Set the default model for a specific type.
    
    Args:
        config: Config instance to update
        model_type: Type of model ('text' or 'vision')
        model_name: Name of the model to set as default
    
    Raises:
        SystemExit: If model_type is invalid
    """
    # Validate model type
    if model_type not in ('text', 'vision'):
        print(f"Error: Model type must be 'text' or 'vision', got '{model_type}'", file=sys.stderr)
        sys.exit(1)
    
    # Set the model
    config.set_model_for_type(model_type, model_name)
    print(f"Default {model_type} model set to: {model_name}")

def set_default_temperature(config: Config, model_type: str, temperature: float) -> None:
    """
    Set the default temperature for a specific type.
    
    Args:
        config: Config instance to update
        model_type: Type of model ('text' or 'vision')
        temperature: Temperature value (0.0-2.0)
    
    Raises:
        SystemExit: If model_type or temperature is invalid
    """
    # Validate model type
    if model_type not in ('text', 'vision'):
        print(f"Error: Model type must be 'text' or 'vision', got '{model_type}'", file=sys.stderr)
        sys.exit(1)
    
    # Validate temperature
    try:
        temp_float = float(temperature)
        if not (0.0 <= temp_float <= 2.0):
            print(f"Error: Temperature must be between 0.0 and 2.0, got {temp_float}", file=sys.stderr)
            sys.exit(1)
    except (ValueError, TypeError):
        print(f"Error: Temperature must be a number, got '{temperature}'", file=sys.stderr)
        sys.exit(1)
    
    # Set the temperature
    try:
        config.set_temperature_for_type(model_type, temp_float)
        print(f"Default {model_type} temperature set to: {temp_float}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def set_default_host(config: Config, model_type: str, host: str) -> None:
    """
    Set the default host for a specific model type.
    
    Args:
        config: Config instance to update
        model_type: Type of model ('text' or 'vision')
        host: Host URL (e.g., 'http://server:11434' or 'server:11434')
    
    Raises:
        SystemExit: If model_type is invalid
    """
    # Validate model type
    if model_type not in ('text', 'vision'):
        print(f"Error: Model type must be 'text' or 'vision', got '{model_type}'", file=sys.stderr)
        sys.exit(1)
    
    # Set the host (normalization happens in config.set_host_for_type)
    config.set_host_for_type(model_type, host)
    normalized_host = config.get_host_for_type(model_type)
    print(f"Default {model_type} host set to: {normalized_host}")

def main(argv: Optional[Sequence[str]] = None) -> None:
    """Main entry point for the ol command."""
    # Initialize configuration on CLI execution (not on import)
    from .init import initialize_ol
    initialize_ol()
    
    parser = argparse.ArgumentParser(
        description='Ollama REPL wrapper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,  # Disable default -h help to use -h for host
        epilog=textwrap.dedent('''
            Examples:
              ol "Explain this code" main.py
              ol -m codellama "Review for security issues" *.py
              ol "What's in this image?" image.jpg
              
              # With remote Ollama instance:
              OLLAMA_HOST=http://server:11434 ol "Your prompt" file.txt
              ol -h server -p 11434 -m llama3.2 "Your prompt" file.txt
              ol -h localhost -p 11435 "Hello"
              
              # Prompt from a file:
              ol -f prompt.txt
              ol --file prompt.txt main.py
              
              # STDIN input (piping/redirection):
              echo "What is Python?" | ol
              ol < file.txt
              echo "code here" | ol "Review this code"
              
              # Set default host for model type:
              ol --set-default-host vision http://server:11434
        ''')
    )
    
    # Add help flags manually
    parser.add_argument('--help', '-?', action='help',
                       help='Show this help message and exit')

    # Version management arguments
    parser.add_argument('--version', action='store_true',
                       help='Show version information')
    parser.add_argument('--check-updates', action='store_true',
                       help='Check for available updates')
    parser.add_argument('--update', action='store_true',
                       help='Update to the latest version if available')

    # Existing arguments
    parser.add_argument('-l', '--list', action='store_true', 
                       help='List available models (works with both local and remote instances)')
    model_arg = parser.add_argument(
        '-m', '--model',
        help='Model to use (default: from config). Vision models need absolute paths for remote.',
    )
    model_arg.completer = complete_model_name
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Show debug information including API request details and equivalent shell commands')
    file_arg = parser.add_argument(
        '-f', '--file', metavar='PROMPTFILE',
        help='Read prompt text from a file',
    )
    file_arg.completer = FilesCompleter()
    parser.add_argument('--save-modelfile', action='store_true',
                       help='Download and save the Modelfile for the specified model')
    parser.add_argument('-a', '--all', action='store_true',
                       help='Save Modelfiles for all models (requires --save-modelfile)')
    output_dir_arg = parser.add_argument(
        '--output-dir',
        help='Output directory for saved Modelfile (default: current working directory)',
    )
    output_dir_arg.completer = DirectoriesCompleter()
    parser.add_argument('-h', '--host', default=None,
                       help='Ollama host (default: localhost). Overrides OLLAMA_HOST and configured hosts for this command.')
    parser.add_argument('-p', '--port', type=int, default=None,
                       help='Ollama port (default: 11434). Overrides OLLAMA_HOST and configured hosts for this command.')
    set_default_model_arg = parser.add_argument(
        '--set-default-model', nargs=2, metavar=('TYPE', 'MODEL'),
        help='Set default model for type (text or vision). Usage: --set-default-model TYPE MODEL_NAME',
    )
    set_default_model_arg.completer = complete_model_type_then_model
    set_default_temperature_arg = parser.add_argument(
        '--set-default-temperature', nargs=2, metavar=('TYPE', 'TEMPERATURE'),
        help='Set default temperature for type (text or vision). Usage: --set-default-temperature TYPE TEMP',
    )
    set_default_temperature_arg.completer = complete_model_type
    set_default_host_arg = parser.add_argument(
        '--set-default-host', nargs=2, metavar=('TYPE', 'HOST'),
        help='Set default host for type (text or vision). Usage: --set-default-host TYPE HOST_URL',
    )
    set_default_host_arg.completer = complete_model_type
    parser.add_argument('--temperature', type=float,
                       help='Temperature for this command (0.0-2.0, overrides default)')
    prompt_arg = parser.add_argument(
        'prompt', nargs='?', default=None,
        help='Prompt to send to Ollama (optional if files are provided)',
    )
    prompt_arg.completer = FilesCompleter()
    files_arg = parser.add_argument(
        'files', nargs='*',
        help='Files to inject into the prompt (text/code, PDFs, images). PDFs are summarized via text extraction; for remote vision models, use absolute image paths.',
    )
    files_arg.completer = FilesCompleter()

    # Shell tab completion (no-op unless _ARGCOMPLETE is set by the shell)
    argcomplete.autocomplete(parser)

    args = parser.parse_args(argv)

    # Normalize and set OLLAMA_HOST if host or port flags are provided
    if args.host is not None or args.port is not None:
        host = args.host if args.host is not None else 'localhost'
        port = args.port if args.port is not None else 11434
        value = f'{host}:{port}'
        if not value.startswith('http://') and not value.startswith('https://'):
            value = f'http://{value}'
        os.environ['OLLAMA_HOST'] = value

    # Initialize config with debug flag
    config = Config(debug=args.debug)

    # Handle set-default-model command
    if args.set_default_model:
        model_type, model_name = args.set_default_model
        set_default_model(config, model_type, model_name)
        sys.exit(0)

    # Handle set-default-temperature command
    if args.set_default_temperature:
        model_type, temperature_str = args.set_default_temperature
        try:
            temperature = float(temperature_str)
            set_default_temperature(config, model_type, temperature)
        except ValueError:
            print(f"Error: Temperature must be a number, got '{temperature_str}'", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    # Handle set-default-host command
    if args.set_default_host:
        model_type, host = args.set_default_host
        set_default_host(config, model_type, host)
        sys.exit(0)

    # Handle version management commands first
    if args.version or args.check_updates or args.update:
        from .version import VersionManager
        vm = VersionManager(debug=args.debug)
        
        if args.version:
            print(vm.get_version_info())
            return
        
        if args.check_updates or args.update:
            # Force check when explicitly requested
            update_available, latest_version, notes_url, update_cmd = vm.check_for_updates(force=True)
            if update_available and latest_version and update_cmd:
                print(vm.format_update_message(latest_version, notes_url, update_cmd))
                if args.update:
                    print("\nInitiating update...")
                    try:
                        # Parse command string into argument list (security: no shell execution)
                        cmd_args = shlex.split(update_cmd)
                        subprocess.run(cmd_args, check=True)
                        print("Update completed successfully!")
                    except subprocess.CalledProcessError as e:
                        print(f"Error during update: {e}", file=sys.stderr)
                        sys.exit(1)
                    except ValueError as e:
                        print(f"Error parsing update command: {e}", file=sys.stderr)
                        sys.exit(1)
            else:
                print("You are using the latest version.")
            return

    if args.list:
        if args.debug:
            print("=== Debug: Listing models ===")
            env = get_env()
            print(format_shell_command(['ollama', 'list'], 
                  env_vars={'OLLAMA_HOST': env['OLLAMA_HOST']} if 'OLLAMA_HOST' in env else None))
        list_models()
        return

    # Validate --all requires --save-modelfile
    if args.all and not args.save_modelfile:
        print("Error: --all requires --save-modelfile", file=sys.stderr)
        sys.exit(1)

    if args.save_modelfile:
        if args.all:
            save_all_modelfiles(args.output_dir, args.debug)
        else:
            if not args.model:
                print("Error: --model is required when using --save-modelfile (or use --all to save all models)", file=sys.stderr)
                sys.exit(1)
            save_modelfile(args.model, args.output_dir, args.debug)
        return

    # Check for STDIN input (piping/redirection)
    stdin_input = None
    if not sys.stdin.isatty():
        # STDIN is available (not a TTY), read it
        try:
            stdin_input = sys.stdin.read()
            if stdin_input:
                stdin_input = stdin_input.rstrip('\n\r')  # Remove trailing newlines
                if args.debug:
                    print(f"DEBUG: Read {len(stdin_input)} characters from STDIN", file=sys.stderr)
        except (IOError, OSError) as e:
            if args.debug:
                print(f"Warning: Failed to read from STDIN: {e}", file=sys.stderr)
            # Continue without STDIN input

    # Check if the first positional argument is a file
    if args.prompt and len(args.prompt) < 255 and not '\n' in args.prompt and (Path(args.prompt).exists() or args.prompt.startswith('~')):
        # If it's a file, move it to files list and set prompt to None
        expanded_path = str(Path(args.prompt).expanduser())
        if Path(expanded_path).exists():
            args.files.insert(0, expanded_path)
            args.prompt = None

    # Handle --file / -f: read prompt text from a file
    if args.file:
        if args.prompt:
            print(
                "Error: cannot use both --file and a prompt argument",
                file=sys.stderr,
            )
            sys.exit(1)
        prompt_path = Path(args.file).expanduser()
        if not prompt_path.exists():
            print(
                f"Error: Prompt file not found: {args.file}",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                file_prompt = f.read()
            args.prompt = file_prompt.rstrip('\n\r')
            if args.debug:
                print(
                    f"DEBUG: Read prompt from file {prompt_path} "
                    f"({len(args.prompt)} characters)",
                    file=sys.stderr,
                )
        except (IOError, OSError, UnicodeDecodeError) as e:
            print(
                f"Error: Failed to read prompt file '{args.file}': {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Handle STDIN input - if present, use it as prompt (or combine with existing prompt)
    if stdin_input:
        if args.prompt:
            # Combine STDIN with existing prompt
            args.prompt = f"{stdin_input}\n\n{args.prompt}"
            if args.debug:
                print(f"DEBUG: Combined STDIN input with prompt argument", file=sys.stderr)
        else:
            # Use STDIN as prompt
            args.prompt = stdin_input
            if args.debug:
                print(f"DEBUG: Using STDIN input as prompt", file=sys.stderr)

    # Handle case where only files are provided
    if not args.prompt and args.files:
        # Use the first file to determine the model type and default prompt
        model_type, default_prompt = get_file_type_and_prompt(args.files[0], config)
        args.prompt = default_prompt
        if not args.model:  # If model not explicitly specified
            args.model = config.get_model_for_type(model_type)
    elif not args.prompt and not args.files and not stdin_input:
        # No prompt, no files, no STDIN - show defaults
        display_defaults(config, get_env())
        sys.exit(0)

    # Check for updates on normal command execution (if enabled)
    try:
        from .version import VersionManager
        vm = VersionManager()
        update_available, latest_version, notes_url, update_cmd = vm.check_for_updates()
        if update_available and latest_version and update_cmd:
            print(vm.format_update_message(latest_version, notes_url, update_cmd))
            print()  # Add a blank line before continuing
    except Exception:
        pass  # Silently ignore any version check errors

    # Determine if CLI host flags were provided
    cli_host_provided = args.host is not None or args.port is not None
    
    run_ollama(args.prompt, args.model, args.files, args.temperature, args.debug, cli_host_provided)

if __name__ == '__main__':
    main() 