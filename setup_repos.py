#!/usr/bin/env python3
"""
Setup script for Koha-doc-translator repositories

This script clones the required repositories for the Koha manual translator:
1. koha-manual from GitLab
2. koha-manual-l10n from GitLab

If the repositories already exist, it updates them to the latest version.
With the --reset flag, it will remove existing repositories and clone them fresh.
"""

import os
import subprocess
import sys
import shutil
import argparse
from pathlib import Path

# Repository URLs
KOHA_MANUAL_REPO = "https://gitlab.com/koha-community/koha-manual.git"
KOHA_MANUAL_L10N_REPO = "https://gitlab.com/koha-community/koha-manual-l10n.git"

# Repository paths
BASE_DIR = Path(__file__).parent
REPOS_DIR = BASE_DIR / "repos"
KOHA_MANUAL_DIR = REPOS_DIR / "koha-manual"
KOHA_MANUAL_L10N_DIR = REPOS_DIR / "koha-manual-l10n"

def run_command(command, cwd=None):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            shell=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error details: {e.stderr}")
        return None

def setup_repo(repo_url, repo_dir, repo_name):
    """Setup a repository - clone if it doesn't exist, update if it does"""
    if repo_dir.exists() and (repo_dir / ".git").exists():
        print(f"Updating existing {repo_name} repository...")
        # Pull the latest changes
        result = run_command("git pull", cwd=repo_dir)
        if result is not None:
            print(f"✅ Successfully updated {repo_name}")
        else:
            print(f"❌ Failed to update {repo_name}")
            return False
    else:
        # Create directory if needed
        if repo_dir.exists():
            print(f"Removing existing directory at {repo_dir}...")
            run_command(f"rm -rf {repo_dir}")
        
        # Make sure parent directory exists
        repo_dir.parent.mkdir(exist_ok=True)
        
        print(f"Cloning {repo_name} repository...")
        result = run_command(f"git clone {repo_url} {repo_dir}")
        if result is not None:
            print(f"✅ Successfully cloned {repo_name}")
        else:
            print(f"❌ Failed to clone {repo_name}")
            return False
    return True

def remove_repos_directory():
    """Remove the repos directory if it exists"""
    if REPOS_DIR.exists():
        print(f"Removing existing repos directory at {REPOS_DIR}...")
        try:
            shutil.rmtree(REPOS_DIR)
            print("✅ Successfully removed repos directory")
            return True
        except Exception as e:
            print(f"❌ Failed to remove repos directory: {e}")
            return False
    return True  # Nothing to remove

def main():
    """Main function to setup repositories"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Setup repositories for Koha Manual Translator')
    parser.add_argument('--reset', action='store_true', help='Remove existing repositories and clone them fresh')
    args = parser.parse_args()
    
    print("Setting up repositories for Koha Manual Translator...")
    
    # If reset flag is provided, remove the repos directory
    if args.reset:
        if not remove_repos_directory():
            print("❌ Reset failed. Exiting.")
            return 1
    
    # Create repos directory if it doesn't exist
    if not REPOS_DIR.exists():
        print(f"Creating repos directory at {REPOS_DIR}...")
        REPOS_DIR.mkdir()
    
    # Setup koha-manual repository
    koha_manual_success = setup_repo(
        KOHA_MANUAL_REPO, 
        KOHA_MANUAL_DIR,
        "koha-manual"
    )
    
    # Setup koha-manual-l10n repository
    koha_manual_l10n_success = setup_repo(
        KOHA_MANUAL_L10N_REPO, 
        KOHA_MANUAL_L10N_DIR,
        "koha-manual-l10n"
    )
    
    # Check if all setups were successful
    if koha_manual_success and koha_manual_l10n_success:
        print("\n✅ All repositories have been set up successfully!")
        print("\nYou can now run the translator with:")
        print("python translator.py --translate --all")
        if args.reset:
            print("\nNote: Repositories were reset to a clean state.")
    else:
        print("\n❌ Repository setup failed")
        print("Please check the error messages above and try again.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
