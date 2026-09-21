# Python Coding Standards

> Scope: Python scripts, tools, test suites, and automation across Antigravity projects.
> Assumes `coding-philosophy.md` also applies.

## Python Environment & Dependencies

- **Standard Library First:** For core lifecycle hooks, CLI utilities, and developer tooling, prefer Python standard library only (`json`, `re`, `sys`, `os`, `pathlib`, `unittest`).
- **Zero Third-Party Pip Dependencies for Hooks:** Lifecycle hooks must execute cleanly on any machine with Python 3.8+ installed without needing `pip install`.
- **Virtual Environments:** For applications and non-hook libraries, use a virtual environment (`.venv`) and pin dependencies with `requirements.txt` or `pyproject.toml`.

## Formatting & Code Style

- Follow **PEP 8** conventions.
- 4 spaces per indentation level. No tabs.
- Maximum line length: 100 characters for code, 120 for comments/strings where readability benefits.
- Snake_case for function and variable names (`handle_pre_tool_use`, `file_path`).
- PascalCase for class names (`TestAgyHooks`).
- UPPER_SNAKE_CASE for module-level constants (`READONLY_COMMAND_PATTERNS`).

## Type Hints & Documentation

- Annotate function parameters and return types:
  ```python
  def handle_pre_tool_use(payload: dict) -> dict: ...
  ```
- Write docstrings for all public functions, classes, and modules adhering to PEP 257.
- Use explicit exception types rather than bare `except:`.

## Testing

- Use standard library `unittest` or `pytest`.
- Run tests via standard module discovery:
  ```powershell
  python -m unittest discover -s tests -p "test_*.py" -v
  ```
- Maintain 100% pass rate on test suites before declaring work complete.

## Cross-Platform Compatibility

- Always use `pathlib.Path` or `os.path.join()` for path manipulations; never hardcode Unix `/` or Windows `\` path separators.
- Handle encoding explicitly (`encoding="utf-8"`) when reading or writing text files.
- Ensure scripts run cleanly on both Windows (PowerShell/CMD) and POSIX systems (Linux/macOS).
