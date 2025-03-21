"""
Setup Figures Directory

This script copies generated figures from static/figures to a local figures directory
in the current directory, making it easier to include them in Markdown documents.
"""

import os
import shutil
import sys

def ensure_dir(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")
    return directory

def copy_figures(source_dir='static/figures', target_dir='figures'):
    """
    Copy all figures from source_dir to target_dir.
    
    Args:
        source_dir (str): Source directory containing figures
        target_dir (str): Target directory to copy figures to
    """
    # Ensure directories exist
    if not os.path.exists(source_dir):
        print(f"Error: Source directory {source_dir} does not exist.")
        return False
    
    ensure_dir(target_dir)
    
    # Copy all files
    count = 0
    for filename in os.listdir(source_dir):
        source_file = os.path.join(source_dir, filename)
        target_file = os.path.join(target_dir, filename)
        
        if os.path.isfile(source_file):
            shutil.copy2(source_file, target_file)
            print(f"Copied: {filename}")
            count += 1
    
    print(f"\nSuccessfully copied {count} files from {source_dir} to {target_dir}")
    return True

def main():
    """Main function to copy figures."""
    print("Setting up figures directory...")
    
    # Parse command-line arguments
    source_dir = 'static/figures'
    target_dir = 'figures'
    
    if len(sys.argv) > 1:
        source_dir = sys.argv[1]
    if len(sys.argv) > 2:
        target_dir = sys.argv[2]
    
    success = copy_figures(source_dir, target_dir)
    
    if success:
        print("\nFigures setup complete!")
        print("\nTo include figures in your paper, use syntax like:")
        print('![Figure Title](figures/filename.png "Figure Title")')
    else:
        print("\nFailed to setup figures.")
        print("Make sure you've generated figures using the sample scripts first.")

if __name__ == "__main__":
    main() 