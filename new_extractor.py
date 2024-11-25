import os

# Define the main project directory to include
project_dir = os.getcwd()
output_file = 'cs_nea_combined_code.md'  # Use Markdown extension for highlighting

# Define folders and files to exclude
exclude_dirs = ['.git', 'node_modules', 'venv', 'env', '__pycache__', 'CACHE', 'src', 'migrations', 'theme']
exclude_files = ['db.sqlite3', 'README.md', 'TODO.md', 'cs_nea_combined_code.md', 'requirements.txt', 'new_extractor.py',
                 '.gitignore', '.prettierrc', 'celerybeat-schedule.bak', 'celerybeat-schedule.dat', 'celerybeat-schedule.dir']  # Database file to exclude
image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico']  # Image file extensions

# Map file extensions to languages for syntax highlighting
extension_to_language = {
    '.py': 'python',
    '.html': 'html',
    '.css': 'css',
    '.js': 'javascript',
    '.json': 'json',
    '.txt': 'plaintext',
    '.md': 'markdown'
}

def collect_project_code_with_highlighting(base_dir, output_path):
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(base_dir):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            # Write directory header
            rel_dir_path = os.path.relpath(root, base_dir)
            if rel_dir_path != ".":
                outfile.write(f"\n# Directory: {rel_dir_path}\n\n")

            # Write files after listing folders
            for file in files:
                # Skip excluded files and pregenerated JSON or image files
                if (
                    file in exclude_files or 
                    file.endswith(tuple(image_extensions)) or 
                    (file.endswith('.json') and 'modified' not in file.lower())
                ):
                    continue
                
                # Add a section header for each file
                file_path = os.path.join(root, file)
                file_extension = os.path.splitext(file)[1]
                language = extension_to_language.get(file_extension, 'plaintext')
                outfile.write(f"\n# File: {os.path.relpath(file_path, base_dir)} \n\n")
                outfile.write(f"```{language}\n")  # Start code block with language
                
                # Attempt to read the file content
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                except UnicodeDecodeError:
                    outfile.write(f"[Could not decode file: {file_path}]\n")
                
                outfile.write("\n```\n")  # End code block

# Collect and save the code
collect_project_code_with_highlighting(project_dir, output_file)

print(f"Code with syntax highlighting collected into {output_file}")
