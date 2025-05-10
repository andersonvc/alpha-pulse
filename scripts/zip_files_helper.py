import os
import zipfile
import argparse
from pathlib import Path

def load_gitignore(gitignore_path):
    from pathspec import PathSpec
    with open(gitignore_path, 'r') as f:
        lines = f.readlines()
    return PathSpec.from_lines('gitwildmatch', lines)

def zip_folder_with_gitignore(source_folder, zip_path, gitignore_path):
    source_folder = Path(source_folder).resolve()
    gitignore_spec = load_gitignore(gitignore_path)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_folder):
            rel_root = os.path.relpath(root, source_folder)
            for file in files:
                full_path = Path(root) / file
                rel_path = Path(rel_root) / file if rel_root != '.' else Path(file)
                if not gitignore_spec.match_file(str(rel_path)):
                    zipf.write(full_path, arcname=rel_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Zip a folder excluding files matched by a .gitignore')
    parser.add_argument('source_folder', help='Path to the folder to zip')
    parser.add_argument('zip_path', help='Output zip file path')
    parser.add_argument('gitignore_path', help='Path to .gitignore file')
    args = parser.parse_args()

    zip_folder_with_gitignore(args.source_folder, args.zip_path, args.gitignore_path)