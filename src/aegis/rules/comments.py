import re


class CommentPreprocessor:
    """Preprocesses SQL raw text to identify rule directives inside comments."""

    @staticmethod
    def has_directive(raw_content: str, directive: str) -> bool:
        """Checks if a specific directive comment exists in the raw content.

        Args:
            raw_content: The raw SQL string contents.
            directive: The target directive (e.g. 'aegis:allow-destructive').

        Returns:
            True if the directive is found inside SQL comments, False otherwise.
        """
        # Match standard SQL line comment starting with -- or block comment /* ... */
        pattern = re.compile(
            rf"(?:--\s*{re.escape(directive)})|(/\*\s*{re.escape(directive)}\s*\*/)"
        )
        return bool(pattern.search(raw_content))
