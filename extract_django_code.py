import os
import argparse
import json

def load_ignore_list(project_path):
    ignore_file = os.path.join(project_path, 'ignore_list.json')
    if os.path.exists(ignore_file):
        with open(ignore_file, 'r') as f:
            return set(json.load(f))
    return set(['.git', 'node_modules', 'venv', 'env', '__pycache__', 'CACHE', 'src', 'migrations', 'extract_django_code.py', 'extract_django_code', 'theme'])

def save_ignore_list(project_path, ignore_dirs):
    ignore_file = os.path.join(project_path, 'ignore_list.json')
    with open(ignore_file, 'w') as f:
        json.dump(list(ignore_dirs), f)

def print_ignored_dirs(ignore_dirs):
    print("Ignored directories:")
    for dir in sorted(ignore_dirs):
        print(f"- {dir}")
    print()

def should_ignore(path, ignore_dirs):
    path_parts = path.split(os.sep)
    return any(ignored in path_parts for ignored in ignore_dirs)

def extract_code(project_path, output_file, ignore_dirs, max_file_size, truncate_size):
    total_size = 0
    max_total_size = 10 * 1024 * 1024  # 10 MB limit for the entire output
    file_count = 0

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(project_path):
            # Remove ignored directories from dirs to prevent walking into them
            dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_dirs)]

            for file in files:
                if file.endswith(('.py', '.js', '.html', '.css')):
                    file_path = os.path.join(root, file)
                    
                    if should_ignore(file_path, ignore_dirs):
                        print(f"Skipping ignored file: {file_path}")
                        continue

                    file_size = os.path.getsize(file_path)
                    
                    if file_size > max_file_size:
                        print(f"Skipping large file: {file_path} ({file_size} bytes)")
                        continue  # Skip files larger than max_file_size
                    
                    relative_path = os.path.relpath(file_path, project_path)
                    outfile.write(f"\n\n# File: {relative_path}\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            content = infile.read(truncate_size)
                            if len(content) == truncate_size:
                                content += "\n# ... (file truncated due to size) ..."
                                print(f"Truncated file: {file_path}")
                            outfile.write(content)
                            total_size += len(content)
                            file_count += 1
                    except Exception as e:
                        outfile.write(f"# Error reading file: {str(e)}\n")
                        print(f"Error reading file: {file_path} - {str(e)}")
                    
                    if total_size >= max_total_size:
                        outfile.write("\n\n# Output truncated due to overall size limit")
                        print(f"Output truncated due to overall size limit ({max_total_size} bytes)")
                        return file_count, total_size

    return file_count, total_size

def main():
    parser = argparse.ArgumentParser(description="Extract code from a Django project")
    parser.add_argument("project_path", help="Path to the Django project")
    parser.add_argument("--output", default="extracted_code.txt", help="Name of the output file (default: extracted_code.txt)")
    parser.add_argument("--ignore", nargs='+', help="Additional directories to ignore")
    parser.add_argument("--max-file-size", type=int, default=1024*1024, help="Maximum file size in bytes (default: 1MB)")
    parser.add_argument("--truncate-size", type=int, default=100*1024, help="Truncate files larger than this size in bytes (default: 100KB)")
    
    args = parser.parse_args()
    
    project_path = os.path.abspath(args.project_path)
    output_file = os.path.join(project_path, args.output)
    
    ignore_dirs = load_ignore_list(project_path)
    if args.ignore:
        ignore_dirs.update(args.ignore)
        save_ignore_list(project_path, ignore_dirs)
    
    print_ignored_dirs(ignore_dirs)
    
    file_count, total_size = extract_code(project_path, output_file, ignore_dirs, args.max_file_size, args.truncate_size)
    print(f"\nCode extraction complete.")
    print(f"Files processed: {file_count}")
    print(f"Total size: {total_size} bytes")
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main()