# Contributing to Clipflow

Thank you for your interest in contributing to **clipflow**! 🎬

This document provides guidelines and instructions for contributing. Please read through it before making changes.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Project Structure](#project-structure)
5. [Making Changes](#making-changes)
6. [Testing](#testing)
7. [Code Style](#code-style)
8. [Type Checking](#type-checking)
9. [Documentation](#documentation)
10. [Git Workflow](#git-workflow)
11. [Pull Request Process](#pull-request-process)
12. [Releasing](#releasing)
13. [Reporting Bugs](#reporting-bugs)
14. [Requesting Features](#requesting-features)

---

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to abide by its terms. Please read it before contributing.

---

## Getting Started

### Prerequisites

- **Python**: 3.9 or higher
- **Git**: For version control
- **FFmpeg**: Automatically managed by clipflow (no manual installation needed)
- **pip**: Python package manager

### Quick Setup

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/ronaldgosso/clipflow.git
cd clipflow

# 3. Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install development dependencies
pip install -e ".[dev]"

# 5. Verify setup
pytest
```

---

## Development Setup

### Installing Dependencies

```bash
# Install with all dev dependencies
pip install -e ".[dev]"

# Individual tools
pip install pytest pytest-cov ruff black mypy
```

### Verification

Ensure everything works:

```bash
# Run tests
pytest

# Check test coverage
pytest --cov=clipflow --cov-report=term

# Lint code
ruff check clipflow/ tests/

# Format code
black clipflow/ tests/

# Type check
mypy clipflow/ --ignore-missing-imports
```

All checks should pass with zero errors.

---

## Project Structure

```
clipflow/
├── clipflow/              # Main package
│   ├── __init__.py        # Public API exports (version lives here)
│   ├── core.py            # High-level API: trim(), inspect(), batch()
│   ├── models.py          # Dataclasses: ClipSpec, TimeRange, VideoInfo, etc.
│   ├── parser.py          # Time string parsing utilities
│   ├── cli.py             # CLI entry point (argparse)
│   ├── _ffmpeg.py         # FFmpeg subprocess layer (ONLY module touching subprocess)
│   ├── _ffmpeg_manager.py # FFmpeg binary download & management
│   └── py.typed           # PEP 561 marker for typed package
├── tests/
│   ├── test_clipflow.py   # Core functionality tests
│   └── test_cli.py        # CLI tests
├── examples/              # Example scripts
├── docs/                  # Documentation
├── pyproject.toml         # Project configuration
├── CHANGELOG.md           # Version history
├── CONTRIBUTING.md        # This file
└── CODE_OF_CONDUCT.md     # Community guidelines
```

### Key Design Principles

1. **Zero runtime dependencies** — only stdlib + managed FFmpeg
2. **Single subprocess contact** — only `_ffmpeg.py` imports `subprocess`
3. **Typed throughout** — all public functions have type annotations
4. **Clean separation** — data models, command building, and execution are separate
5. **No dict-based APIs** — everything uses typed dataclasses

---

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-123
```

### 2. Implement Your Changes

Follow the project's coding conventions:

- Use type annotations on all public functions
- Write docstrings following NumPy/SciPy style
- Keep functions small and focused
- Add tests for new functionality
- Update documentation as needed

### 3. Write Tests

All new features must include tests. Tests live in the `tests/` directory.

```python
# Example test structure
class TestYourFeature:
    def test_basic_functionality(self):
        # Arrange
        input_data = ...
        
        # Act
        result = your_function(input_data)
        
        # Assert
        assert result == expected

    def test_edge_case(self):
        # Test boundary conditions
        pass

    def test_error_handling(self):
        with pytest.raises(ValueError, match="expected error message"):
            your_function(invalid_input)
```

### 4. Update Documentation

- Update docstrings for modified functions
- Add examples to the README if applicable
- Update CHANGELOG.md with your changes

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=clipflow --cov-report=term --cov-report=html

# Run specific test file
pytest tests/test_clipflow.py

# Run specific test class
pytest tests/test_clipflow.py::TestYourFeature

# Run specific test
pytest tests/test_clipflow.py::TestYourFeature::test_specific_case
```

### Test Guidelines

- **All tests must pass** before submitting a PR
- **Coverage must stay above 80%** (current: >90%)
- **Mock FFmpeg interactions** — tests should not call actual FFmpeg
- **Use fixtures** for common test setup
- **Test edge cases** and error conditions

### Mocking FFmpeg

The project uses an auto-use fixture to mock FFmpeg management:

```python
@pytest.fixture(autouse=True)
def mock_ffmpeg_manager(tmp_path: Path):
    """Mock ensure_ffmpeg to return fake binary paths."""
    fake_ffmpeg = tmp_path / "fake_ffmpeg.exe"
    fake_ffprobe = tmp_path / "fake_ffprobe.exe"
    fake_ffmpeg.write_bytes(b"")
    fake_ffprobe.write_bytes(b"")

    with patch(
        "clipflow._ffmpeg_manager.ensure_ffmpeg",
        return_value=(fake_ffmpeg, fake_ffprobe),
    ):
        yield
```

---

## Code Style

### Formatting

We use **Black** for code formatting:

```bash
# Format all code
black clipflow/ tests/

# Check without modifying
black --check clipflow/ tests/
```

**Configuration:**
- Line length: 88 characters
- Target Python version: 3.9+

### Linting

We use **Ruff** for linting:

```bash
# Check for issues
ruff check clipflow/ tests/

# Auto-fix fixable issues
ruff check --fix clipflow/ tests/
```

**Enabled rules:**
- `E` — pycodestyle errors
- `F` — pyflakes
- `I` — isort (import ordering)
- `UP` — pyupgrade
- `B` — bugbear
- `SIM` — simplify

### Import Ordering

Imports should be grouped and sorted:

```python
# Standard library
from __future__ import annotations
import json
import logging
from pathlib import Path

# Third-party (if any)
# (Currently none — zero runtime dependencies!)

# Local modules
from clipflow.models import ClipSpec, TimeRange
from clipflow._ffmpeg import run_trim
```

---

## Type Checking

We use **mypy** with strict mode:

```bash
# Type check
mypy clipflow/ --ignore-missing-imports
```

### Type Guidelines

- **All public functions** must have complete type annotations
- **Use `typing` module** for complex types (e.g., `Callable`, `Union`)
- **Prefer explicit types** over `Any`
- **Document return types** in docstrings
- **Use type aliases** for complex types:

```python
from typing import Callable

ProgressCallback = Callable[[int, int, ClipResult], None]

def trim(
    input_path: str | Path,
    clips: ClipSpec | list[ClipSpec],
    *,
    output_dir: str | Path = "output",
    on_progress: ProgressCallback | None = None,
) -> list[ClipResult]:
    ...
```

---

## Documentation

### Docstrings

Use NumPy-style docstrings for all public functions:

```python
def your_function(param1: str, param2: int) -> str:
    """
    Brief description of what the function does.

    Parameters
    ----------
    param1 : str
        Description of param1.
    param2 : int
        Description of param2.

    Returns
    -------
    str
        Description of the return value.

    Raises
    ------
    ValueError
        When param1 is empty.

    Examples
    --------
    >>> your_function("hello", 42)
    'hello-42'
    """
    ...
```

### README Updates

When adding new features:
- Update the relevant section in README.md
- Add examples demonstrating the feature
- Keep the ASCII art and badges intact

---

## Git Workflow

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): brief description

Optional longer description explaining:
- What changed
- Why it changed
- Any breaking changes

type: feat, fix, docs, style, refactor, test, chore
scope: module name or component (optional)
```

**Examples:**

```
feat(_ffmpeg_manager): add automatic FFmpeg binary download
fix(core): handle edge case in time range parsing
docs(README): update installation instructions
test(cli): add tests for batch subcommand
refactor(models): simplify ClipSpec initialization
chore(deps): update pytest to 8.0
```

### Before Committing

```bash
# 1. Run all checks
ruff check clipflow/ tests/ && black clipflow/ tests/
mypy clipflow/ --ignore-missing-imports
pytest

# 2. Review changes
git diff

# 3. Stage files
git add <files>

# 4. Commit
git commit -m "type(scope): your message"
```

---

## Pull Request Process

### Checklist

Before submitting a PR:

- [ ] Code follows style guidelines (Black + Ruff)
- [ ] Type checks pass (mypy strict)
- [ ] All tests pass (pytest)
- [ ] Coverage maintained or improved (>80%)
- [ ] Docstrings added/updated
- [ ] CHANGELOG.md updated
- [ ] Documentation updated (README, examples)
- [ ] Commit messages follow conventions
- [ ] Branch is up-to-date with main

### PR Description Template

```markdown
## Summary
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (requires major version bump)
- [ ] Documentation update
- [ ] Refactoring (no functional change)

## Changes
- List specific changes
- Include rationale if applicable

## Testing
- Describe how changes were tested
- Mention any new tests added

## Checklist
- [ ] Tests pass locally
- [ ] Code formatted (black + ruff)
- [ ] Types checked (mypy)
- [ ] Documentation updated
```

### Review Process

1. **Automated CI checks** must pass
2. **At least one maintainer review** required
3. **Address feedback** and push updates
4. **Merge** once approved

---

## Releasing

Releases are handled by maintainers:

```bash
# 1. Update version in pyproject.toml and clipflow/__init__.py
# 2. Update CHANGELOG.md
# 3. Commit changes
git commit -m "chore: bump version to 0.x.0"

# 4. Tag the release
git tag v0.x.0
git push origin v0.x.0

# 5. GitHub Actions automatically publishes to PyPI
```

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features (backward compatible)
- **PATCH** (0.0.X): Bug fixes (backward compatible)

---

## Reporting Bugs

### Before Reporting

1. Check existing issues to avoid duplicates
2. Verify the bug exists in the latest version
3. Gather relevant information

### Bug Report Template

```markdown
**Describe the bug**
Clear description of what the bug is

**To Reproduce**
Steps to reproduce:
1. `clipflow.trim(...)`
2. See error

**Expected behavior**
What should have happened

**Actual behavior**
What actually happened

**Environment:**
- OS: Windows/Linux/macOS
- Python version: 3.x.x
- clipflow version: 0.x.x

**Additional context**
Logs, stack traces, etc.
```

---

## Requesting Features

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
Describe the problem you're trying to solve

**Describe the solution you'd like**
Clear description of what you want

**Describe alternatives you've considered**
Any alternative approaches

**Additional context**
Examples, mockups, references
```

---

## Questions?

- **General questions**: Open a [GitHub Discussion](https://github.com/ronaldgosso/clipflow/discussions)
- **Bug reports**: Open an [Issue](https://github.com/ronaldgosso/clipflow/issues)
- **Feature requests**: Open an [Issue](https://github.com/ronaldgosso/clipflow/issues)
- **Email**: ronaldgosso@gmail.com

---

## Acknowledgments

Thank you to all contributors who have helped shape clipflow! 

<div align="center"><sub>Built with Python · ffmpeg · subprocess · zero magic</sub></div>
