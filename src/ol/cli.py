#!/usr/bin/env python3

import argparse
import base64
import os
import subprocess
import sys
import shlex
from pathlib import Path
from typing import List, Optional, Sequence, Dict
from .config import Config

def get_env() -> Dict[str, str]:
    """Get environment variables for Ollama."""
    env = os.environ.copy()
    if 'OLLAMA_HOST' in env:
        if env['OLLAMA_HOST'].startswith('http://') or env['OLLAMA_HOST'].startswith('https://'):
            return env
        # Add http:// prefix if not present
        env['OLLAMA_HOST'] = f"http://{env['OLLAMA_HOST']}"
    return env

def list_models() -> None:
    """List all available Ollama models."""
    try:
        subprocess.run(['ollama', 'list'], env=get_env(), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error listing models: {e}", file=sys.stderr)
        sys.exit(1)

def is_image_file(file_path: str) -> bool:
    """Check if the file is an image."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    return Path(file_path).suffix.lower() in image_extensions

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

def run_ollama(prompt: str, model: str = None, files: Optional[List[str]] = None, debug: bool = False) -> None:
    """
    Run Ollama with the given prompt and optional files.
    
    Args:
        prompt: The prompt to send to Ollama
        model: The model to use (if None, will be determined from config)
        files: Optional list of files to inject into the prompt
        debug: Whether to show debug information
    """
    config = Config()
    env = get_env()
    is_remote = 'OLLAMA_HOST' in env
    
    # Determine the model to use
    if model is None:
        if files and any(is_image_file(f) for f in files):
            model = config.get_model_for_type('vision')
        else:
            model = config.get_last_used_model() or config.get_model_for_type('text')
    
    # Save the model as last used
    config.set_last_used_model(model)

    if debug:
        print("\n=== Debug Information ===")
        print(f"Model: {model}")
        print(f"Base Prompt: {prompt}")
        print(f"Files to process: {files if files else 'None'}")
        if is_remote:
            print(f"Ollama Host: {env['OLLAMA_HOST']}")
        print()

    # Process files and build complete prompt
    complete_prompt = prompt
    image_files = []
    text_files = []

    if files:
        for file_path in files:
            if is_image_file(file_path):
                image_files.append(os.path.abspath(file_path))
                if debug:
                    print(f"Added image file: {file_path}")
            else:
                text_files.append(file_path)
                with open(file_path, 'r') as f:
                    file_content = f.read()
                    complete_prompt += f"\n\nContent of {file_path}:\n{file_content}"
                    if debug:
                        print(f"Added content from {file_path}")
                        print(f"File content length: {len(file_content)} characters")

    if debug:
        print("\n=== Command Information ===")
        cmd = ['ollama', 'run', model]
        
        if image_files:
            if is_remote:
                # For remote vision models, include image path in prompt
                vision_prompt = f"{prompt} {' '.join(image_files)}"
                print("Equivalent shell command:")
                print(format_shell_command(cmd, vision_prompt,
                      {'OLLAMA_HOST': env['OLLAMA_HOST']} if is_remote else None))
            else:
                # For local vision models, use base64 pipeline
                print("Equivalent shell command:")
                print(f"base64 -w0 {shlex.quote(image_files[0])} | ollama run {shlex.quote(model)} {shlex.quote(prompt)}")
        else:
            # Show the regular command for text
            print("Equivalent shell command:")
            print(format_shell_command(cmd, complete_prompt, 
                  {'OLLAMA_HOST': env['OLLAMA_HOST']} if is_remote else None))

    try:
        if image_files:
            if is_remote:
                # For remote vision models, include image path in prompt
                vision_prompt = f"{prompt} {' '.join(image_files)}"
                subprocess.run(['ollama', 'run', model],
                             input=vision_prompt.encode(),
                             env=env,
                             check=True)
            else:
                # For local vision models, use base64 pipeline
                for img_file in image_files:
                    base64_process = subprocess.Popen(['base64', '-w0', img_file], 
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE)
                    
                    ollama_process = subprocess.Popen(['ollama', 'run', model, prompt],
                                                    stdin=base64_process.stdout,
                                                    env=env)
                    
                    # Close base64's stdout to signal EOF to ollama
                    base64_process.stdout.close()
                    
                    # Wait for both processes to complete
                    base64_process.wait()
                    ollama_process.wait()
                    
                    if base64_process.returncode != 0:
                        print(f"Error encoding image: {base64_process.stderr.read().decode()}", file=sys.stderr)
                        sys.exit(1)
                    if ollama_process.returncode != 0:
                        print(f"Error running Ollama", file=sys.stderr)
                        sys.exit(1)
        else:
            # Handle text-only input
            subprocess.run(['ollama', 'run', model], 
                         input=complete_prompt.encode(),
                         env=env,
                         check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Ollama: {e}", file=sys.stderr)
        sys.exit(1)

def main(argv: Optional[Sequence[str]] = None) -> None:
    """
    Main entry point for the ol command.
    
    Args:
        argv: Optional list of command line arguments for testing
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Ollama REPL wrapper')
    parser.add_argument('-l', '--list', action='store_true', help='List available models')
    parser.add_argument('-m', '--model', help='Model to use (default: from config)')
    parser.add_argument('-d', '--debug', action='store_true', help='Show debug information')
    parser.add_argument('prompt', nargs='?', help='Prompt to send to Ollama')
    parser.add_argument('files', nargs='*', help='Files to inject into the prompt')

    args = parser.parse_args(argv)
    config = Config()

    if args.list:
        if args.debug:
            print("=== Debug: Listing models ===")
            env = get_env()
            print(format_shell_command(['ollama', 'list'], 
                  env_vars={'OLLAMA_HOST': env['OLLAMA_HOST']} if 'OLLAMA_HOST' in env else None))
        list_models()
        return

    # Check if the first positional argument is a file
    if args.prompt and (Path(args.prompt).exists() or args.prompt.startswith('~')):
        # If it's a file, move it to files list and set prompt to None
        expanded_path = str(Path(args.prompt).expanduser())
        if Path(expanded_path).exists():
            args.files.insert(0, expanded_path)
            args.prompt = None

    # Handle case where only files are provided
    if not args.prompt and args.files:
        # Use the first file to determine the model type and default prompt
        model_type, default_prompt = get_file_type_and_prompt(args.files[0], config)
        args.prompt = default_prompt
        if not args.model:  # If model not explicitly specified
            args.model = config.get_model_for_type(model_type)
    elif not args.prompt and not args.files:
        parser.print_help()
        sys.exit(1)

    run_ollama(args.prompt, args.model, args.files, args.debug)

if __name__ == '__main__':
    main() 