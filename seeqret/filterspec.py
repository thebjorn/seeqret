import re
import logging

logger = logging.getLogger(__name__)


def glob_to_regex(glob_pattern: str) -> str:
    """
    Convert a glob pattern to a regex pattern.

    Parameters:
        glob_pattern (str): The glob pattern to convert.

    Returns:
        str: The equivalent regex pattern.
    """
    # Escape all special characters except for glob-specific ones (*, ?, [])
    regex = re.escape(glob_pattern)

    # Convert glob-specific characters
    # '*' matches zero or more characters
    regex = regex.replace(r'\*', '.*')
    # '?' matches exactly one character
    regex = regex.replace(r'\?', '.')
    # '[!...]' matches any character not in the brackets
    regex = regex.replace(r'\[!', '[^')
    # Allow square brackets for ranges
    regex = regex.replace(r'\[', '[').replace(r'\]', ']')

    # Ensure the regex matches the full string
    return f"^{regex}$"


class FilterSpec:
    def __init__(self, filterspec):
        self.filterspec = filterspec
        parts = filterspec.split(':')
        # print("PARTS:", parts)

        if len(parts) == 1:
            self.app = '*'
            self.env = '*'
            self.name = parts[0] or '*'
        if len(parts) == 2:
            self.app = parts[0] or '*'
            self.env = parts[1] or '*'
            self.name = '*'
        if len(parts) == 3:
            self.app = parts[0] or '*'
            self.env = parts[1] or '*'
            self.name = parts[2] or '*'

        logger.debug("FILTERSPEC: %s == %s", filterspec, str(self))

    def to_filterdict(self):
        return dict(
            app=self.app,
            env=self.env,
            key=self.name,
        )

    def __str__(self):
        return self.app + ':' + self.env + ':' + self.name

    def pattern_to_regex(self, pattern: str):
        return re.compile(glob_to_regex(pattern))

    def match_item(self, val: str, pattern: str) -> bool:
        # print("MATCH:ITEM:", val, pattern, end=' ')
        if pattern == '*':
            # print("TRUE")
            return True
        regex = self.pattern_to_regex(pattern)
        # print("REGEX:", regex)
        # print("MATCH:", regex.match(val))
        return regex.match(val) is not None

    def matches(self, item: (str, str, str)) -> bool:
        return all(self.match_item(val, pattern)
                   for val, pattern
                   in zip(item, (self.app, self.env, self.name)))

    def filter(self, items: list[(str, str, str)]) -> list:
        for item in items:
            # print("ITEM:", item)
            # print("-------------------")
            if self.matches(item):
                yield item
