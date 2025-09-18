import os
import tokenize
import io
import argparse


def remove_python_comments(source_code: str) -> str:
    """
        Removes comments from a Python source string while preserving docstrings.
    9
        This function tokenizes the source code and reconstructs it from the tokens,
        omitting any tokens that are identified as comments. Docstrings are
        treated as STRING tokens and are therefore preserved.

        Args:
            source_code: A string containing the Python source code.

        Returns:
            A string with the comments removed.
    """

    source_io = io.StringIO(source_code)

    tokens_without_comments = []

    try:
        for tok in tokenize.generate_tokens(source_io.readline):
            if tok.type == tokenize.COMMENT and tok.string.startswith("#!"):
                tokens_without_comments.append(tok)

            elif tok.type != tokenize.COMMENT:
                tokens_without_comments.append(tok)
    except tokenize.TokenError as e:
        print(f"Error: Could not tokenize the source. Invalid syntax? - {e}")

        return source_code
    except IndentationError as e:
        print(f"Error: Could not tokenize the source. Indentation error? - {e}")
        return source_code

    return tokenize.untokenize(tokens_without_comments)


def process_file(file_path: str):
    """
    Opens a Python file, removes comments, and saves it back.

    Args:
        file_path: The full path to the Python file.
    """
    print(f"Processing: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            original_source = f.read()

        cleaned_source = remove_python_comments(original_source)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_source)

    except Exception as e:
        print(f"  -> Failed to process {file_path}: {e}")


def main():
    """
    Main function to parse command-line arguments and start the process.
    """
    parser = argparse.ArgumentParser(
        description="Recursively find all Python files in a folder and remove comments, keeping docstrings.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "folder", help="The path to the folder to search for .py files."
    )
    args = parser.parse_args()

    target_folder = args.folder

    if not os.path.isdir(target_folder):
        print(f"Error: '{target_folder}' is not a valid directory.")
        return

    print(f"Starting to remove comments from .py files in '{target_folder}'...")

    for root, _, files in os.walk(target_folder):
        for filename in files:
            if filename.endswith(".py"):
                file_path = os.path.join(root, filename)
                process_file(file_path)

    print("\nProcessing complete.")


if __name__ == "__main__":
    main()
