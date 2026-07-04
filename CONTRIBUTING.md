# Contributing to Aegis

Thank you for your interest in contributing to Aegis! This document outlines the guidelines, workflows, and standards to keep in mind when contributing.

## Development Workflow

### Setup Instructions

Aegis is developed using Python 3.11+. We recommend using [uv](https://github.com/astral-sh/uv) or a standard Python virtual environment.

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/your-username/aegis.git
   cd aegis
   ```

2. **Establish Environment & Install Dependencies**:
   * **Using `uv` (recommended)**:
     ```bash
     uv sync --all-groups
     ```
   * **Using standard `venv`**:
     ```bash
     python -m venv .venv
     # Windows
     .venv\Scripts\activate
     # macOS / Linux
     source .venv/bin/activate

     python -m pip install --upgrade pip
     pip install -e .[dev,test]
     ```

3. **Install Pre-Commit Hooks**:
   ```bash
   pre-commit install
   ```

### Development Loop

When writing code or adding features:
1. Run local tests: `pytest`
2. Validate types: `mypy src tests`
3. Check code formatting: `ruff check` and `ruff format`

---

## Branch Naming Conventions

Always create feature/bugfix branches off the `develop` branch. Use descriptive names prefixed by change categories:

* `feature/` - Adding new CLI capabilities, rules, or core modules (e.g. `feature/add-drop-table-rule`)
* `bugfix/` - Fixing incorrect parser behavior, warnings, or crashes (e.g. `bugfix/parse-null-constraint`)
* `docs/` - Enhancements to README, guides, or docstrings (e.g. `docs/update-roadmap`)
* `refactor/` - Structural adjustments without functional changes (e.g. `refactor/config-parser`)
* `chore/` - Repository updates, CI changes, or package increments (e.g. `chore/bump-dependencies`)

---

## Commit Message Conventions

We adhere strictly to the **Conventional Commits** specification. Every commit message must follow this format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Supported Commit Types
* `feat`: A new user-facing feature.
* `fix`: A bug fix.
* `docs`: Documentation updates.
* `style`: Styling or formatting (white-space, semi-colons) changes.
* `refactor`: Structural codebase improvements.
* `perf`: Execution speed or memory footprint enhancements.
* `test`: Adding or amending test cases.
* `ci`: Workflow or automation changes.
* `chore`: Package building or external configuration maintenance.

### Scope Guidelines
The `<scope>` should name the module or subsystem changed (e.g., `cli`, `config`, `rules`, `parser`). 

Example:
```
feat(rules): add safety check for dropping database indexes
```

---

## Pull Request Process

1. **Pull Latest Changes**: Ensure your branch is updated with the latest commits from the `develop` branch.
2. **Review Code standards**: Run pytest, ruff, and mypy locally. Verify that your tests pass.
3. **Submit PR**: Target your PR to merge into the `develop` branch.
4. **Pass Checks**: Confirm that all GitHub Actions CI checks complete successfully.
5. **Code Review**: At least one maintainer must review and approve your changes before merging.

---

## Coding Standards

To maintain high code quality, Aegis enforces strict coding standards:
* **Python version compatibility**: The codebase must be compatible with Python 3.11+.
* **Style Rules**: Checked and enforced by Ruff (configured to follow Black formatting standards with 88-character maximum line length).
* **Strict Typing**: All functions, variables, and parameters must be explicitly typed. Mypy checks are run in `--strict` mode.
* **Docstrings**: Add Google-style docstrings for all new modules, classes, and public interfaces.
