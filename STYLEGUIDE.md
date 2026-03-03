# Style guide
(original version: dktools/data/STYLEGUIDE.md)

This style guide outlines the conventions and best practices for writing code in this project. Adhering to these guidelines will help maintain consistency, readability, and quality across the codebase.

This package uses

- [x] python
- [ ] svelte
- [ ] typescript
- [ ] javascript
- [ ] html
- [ ] css
- [ ] scss
- [ ] less

Use the relevant MCP servers and/or LSP servers when available.

## General Principles

- Write clear and descriptive comments.
- Use meaningful variable and function names (use i,j,k only for loop indices).
- Keep functions and methods short and focused on a single task.
- Avoid deep nesting of code blocks.
- Use docstrings (python) or JSDoc (JavaScript/TypeScript) for documenting functions, classes, and modules.
- Follow language-specific best practices and conventions, except where overridden by this style guide.

## Formatting

- Use 4 spaces for indentation (no tabs).
- Limit lines to a maximum of 79 characters (preferably, up to 100 if needed). HTML can use longer lines if it improves readability.
- use blank lines to separate thoughts inside functions (e.g., between logical blocks of code).
- Prefer single quotes for strings unless the string contains a single quote character.
- Place imports at the top of the file, grouped by standard library, third-party, and local imports.

## Naming Conventions
Follow these naming conventions even in languages that normally use different conventions:

- Use `snake_case` for variable and function names.
- Use `PascalCase` for class names.
- Use `UPPER_SNAKE_CASE` for constants.
- Use kebab-case for file, directory, and url names.
- use required casing where dictated by frameworks or libraries (e.g., React components, Svelte components, etc.).
  (e.g. use toString() in JavaScript, not to_string())

## Quotes

Use single quotes for strings unless the string contains a single quote character.
Don't change existing quotes.

## Data Structures Formatting
### List of values
Lists of values should be formatted like this:

    variable = [
        value1,
        value2,
        value3,
    ]

except for short lists that fit on one line:

    variable = [value1, value2, value3]

### List of objects/dicsts

Lists of objects should be formatted like this:

    variable = [{
        property: value,
        property2: value2,
    }, {
        property: value,
        property2: value2,
    }]

### Dict of lists

Dicts of lists should be formatted like this:

    variable = {
        key1: [value1, value2],
        key2: [value1, value2],
    }

### Dict of dicts

Dicts of dicts should be formatted like this:

    variable = {
        key1: {
            property: value,
            property2: value2,
        },
        key2: {
            property: value,
            property2: value2,
        },
    }

# Python Specific Guidelines
Follow PEP 8 guidelines except as noted below.
[PEP 8 -- Style Guide for Python Code](https://raw.githubusercontent.com/python/peps/refs/heads/main/peps/pep-0008.rst)

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
