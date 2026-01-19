# Style guide

This style guide outlines the conventions and best practices for writing code in this project. Adhering to these guidelines will help maintain consistency, readability, and quality across the codebase.

## General Principles

- Follow PEP8 guidelines for Python code except as noted below.
- Write clear and descriptive comments.
- Use meaningful variable and function names (use i,j,k only for loop indices).
- Keep functions and methods short and focused on a single task.

## Formatting

- Use 4 spaces for indentation (no tabs).
- Limit lines to a maximum of 79 characters (preferably, up to 100 if needed).
- use blank lines to separate thoughts inside functions (e.g., between logical blocks of code).
- Prefer single quotes for strings unless the string contains a single quote character.
- Place imports at the top of the file, grouped by standard library, third-party, and local imports.


## Naming Conventions
- Use `snake_case` for variable and function names.
- Use `PascalCase` for class names.
- Use `UPPER_SNAKE_CASE` for constants.
- Use kebab-case for file and directory names.

## Comments and Documentation
- Write docstrings for all public modules, functions, and classes.
- Use inline comments for complex or non-obvious code.

Docstring format example:
```python
def example_function(param1, param2):
    """Single line docstring.
    """
    pass


def another_example(param1, param2):
    """Summary line.

       Extended description of function, note the indentation, under the
       first letter of the summary line.
    """
    pass
```
