from typing import List, Optional
from arch.crawler import crawl_package, render_tree, to_json


def main(argv: Optional[List[str]] = None) -> int:
    """Command-line entry point.

    Parses arguments, crawls the given path, and prints either a tree or JSON.

    Args:
        argv (Optional[List[str]]): Argument vector, e.g. ``["path", "--format", "json"]``. If ``None``, sys.argv is used.

    Returns:
        int: Process exit code. ``0`` on success.

    Examples:
    - Invoke main with a temporary directory and JSON output while capturing stdout
        ```python

        >>> import io, contextlib, tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     buf = io.StringIO()
        ...     with contextlib.redirect_stdout(buf):
        ...         rc = main([d, '--format', 'json', '--indent', '0'])
        ...     rc == 0 and '"modules"' in buf.getvalue()
        True

        ```

    See Also:
        crawl_package: Builds the model printed by this function.
        render_tree: Renders a human-friendly tree.
        to_json: Serializes the model to JSON.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Crawl a Python package directory and output its structure.")
    parser.add_argument("path", help="Path to the root directory of the package or repository")
    parser.add_argument("--format", choices=["tree", "json"], default="tree", help="Output format")
    parser.add_argument("--indent", type=int, default=2, help="JSON indent")
    args = parser.parse_args(argv)

    model = crawl_package(args.path)
    if args.format == "json":
        print(to_json(model, indent=args.indent))
    else:
        print(render_tree(model))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())