# pyright: strict


def unindent(text: str) -> str:
    """
    Convenience function to unindent multi-line strings in tests.

    Useful for when defining indent-sensitive multi line strings but wanting
    to keep the indentation level in the source code aligned with the rest of
    the code.

    Also removes the leading and trailing newlines characters so the \"\"\" can
    be on their own lines.

    Example:
    ```python
        unindent(\"\"\"
            line 1
                line 2
            line 3
        \"\"\")
        # returns "line 1\\n    line 2\\nline 3"
    ```
    """

    lines: list[str] = text.splitlines()

    # find minimum indentation (ignore empty lines)
    min_indent: int = min(
        (len(line) - len(line.lstrip()))
        for line in lines
        if line.strip()
    )

    # remove indentation
    unindented: str = '\n'.join(line[min_indent:] for line in lines)

    # remove leading & trailing newlines
    trimmed: str = unindented[1:-1]

    return trimmed
