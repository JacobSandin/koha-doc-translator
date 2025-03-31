#!/usr/bin/env python3
"""
Simple script to build the Swedish Koha manual using make.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def run_command(command, cwd=None, env=None):
    """Run a shell command and return the output"""
    logging.info(f"Running command: {command}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            shell=True,
            env=env
        )
        logging.info(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing command: {command}")
        logging.error(f"Error details: {e.stderr}")
        return False

def check_repositories():
    """Check if the required repositories are set up correctly"""
    base_dir = Path(__file__).parent
    koha_manual_dir = base_dir / "repos" / "koha-manual"
    locales_dir = koha_manual_dir / "locales"
    
    if not koha_manual_dir.exists():
        logging.error(f"Koha manual repository not found at {koha_manual_dir}")
        logging.info("Please run setup_repos.py first to set up the repositories.")
        return False, None
    
    if not locales_dir.exists():
        logging.error(f"Localization repository not found at {locales_dir}")
        logging.info("Please run setup_repos.py first to set up the repositories.")
        return False, None
    
    # Check if Swedish translations exist
    sv_dir = locales_dir / "sv"
    if not sv_dir.exists():
        logging.error(f"Swedish translations not found at {sv_dir}")
        logging.info("Make sure you've run the translator to generate Swedish translations.")
        return False, None
    
    logging.info("All required repositories are set up correctly.")
    return True, koha_manual_dir

def build_swedish_manual():
    """Build the Swedish manual using make"""
    # Check if repositories are set up correctly
    repos_ok, koha_manual_dir = check_repositories()
    if not repos_ok:
        return 1
    
    # Set environment variables for the build
    env = os.environ.copy()
    env['LC_ALL'] = 'C.UTF-8'
    env['LANG'] = 'C.UTF-8'
    env['LANGUAGE'] = 'sv'
    
    # Build the Swedish manual using make
    command = 'make -e SPHINXOPTS="-q -D language=\'sv\' -d build/doctrees" BUILDDIR="build/sv" singlehtml'
    if run_command(command, cwd=koha_manual_dir, env=env):
        build_dir = koha_manual_dir / "build" / "sv" / "singlehtml"
        logging.info(f"Successfully built Swedish manual")
        logging.info(f"Output is available at: {build_dir}")
        logging.info(f"You can open the manual at: file://{build_dir}/index.html")
        return 0
    else:
        logging.error("Failed to build Swedish manual")
        return 1

if __name__ == "__main__":
    sys.exit(build_swedish_manual())
