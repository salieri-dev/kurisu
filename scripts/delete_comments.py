import io
import os
import sys
import tokenize


def remove_comments_only(source_code):
    """
    Removes only single-line comments (#) from a Python source code string.
    Docstrings are preserved.
    """
    try:
        source_readline = io.StringIO(source_code).readline
        tokens = tokenize.generate_tokens(source_readline)

        result_tokens = [token for token in tokens if token.type != tokenize.COMMENT]

        return tokenize.untokenize(result_tokens)
    except tokenize.TokenError as e:
        print(f"  -> Skipping file due to token error: {e}")
        return source_code


def process_python_file(file_path):
    """
    Opens a Python file, removes comments, and overwrites the original file.
    """
    print(f"Processing: {file_path}")
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            source = f.read()

        if not source.strip():
            return

        cleaned_source = remove_comments_only(source)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_source)

    except Exception as e:
        print(f"ERROR: Could not process {file_path}. Reason: {e}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python remover.py <path_to_your_code_folder>")
        sys.exit(1)

    target_path = sys.argv[1]

    if not os.path.exists(target_path):
        print(f"Error: Path '{target_path}' does not exist.")
        sys.exit(1)

    ignore_dirs = {"venv", ".venv", "env", ".env", "__pycache__", ".git"}
    print(f"Ignoring directories named: {', '.join(ignore_dirs)}\n")

    if os.path.isfile(target_path):
        if target_path.endswith(".py"):
            process_python_file(target_path)
    elif os.path.isdir(target_path):
        print(f"Scanning directory: {target_path}")

        for root, dirs, files in os.walk(target_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    process_python_file(file_path)

    print("\nOperation complete.")


if __name__ == "__main__":
    main()
