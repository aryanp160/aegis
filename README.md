# Aegis

[![CI](https://github.com/aryanp160/aegis/actions/workflows/ci.yml/badge.svg)](https://github.com/aryanp160/aegis/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/)

Aegis is a production-quality, open-source static analyzer for Python SQL migrations. It parses migration files, builds abstract syntax trees (ASTs), and inspects changes against safety rules to prevent destructive database schema modifications (e.g., locking tables, dropping columns, or modifying types in ways that disrupt live systems).

---

## 🛠️ Architecture & Dependency Selection

Aegis relies on a carefully curated, modern stack to ensure high performance, developer convenience, and reliability. Below is the rationale behind each primary dependency:

| Dependency | Purpose | Rationale |
| :--- | :--- | :--- |
| **`sqlglot`** | SQL Parsing & Dialects | A robust, pure-python SQL parser, transpiler, and analyzer. Unlike simple regex-based parsers, `sqlglot` builds complete, detailed ASTs and supports dozens of SQL dialects (PostgreSQL, MySQL, SQLite, Oracle, Snowflake, etc.), making it perfect for multi-dialect static analysis. |
| **`typer`** | Command Line Interface | Enables rapid building of user-friendly CLIs based on standard Python type hints. It automatically generates beautiful, interactive help menus and validates CLI input. |
| **`rich`** | Terminal Formatting | Aegis demands rich visual presentation for static analysis warnings, tables, progress indicators, and syntax-highlighted SQL. `rich` is the industry standard for creating gorgeous console UIs. |
| **`pydantic`** | Validation & Settings | Aegis config files are validated using Pydantic. It allows users to write simple config files (JSON/TOML/YAML) and compiles them into type-safe Python objects with descriptive error messages when configurations are malformed. |
| **`ruff`** | Linting & Formatting | An extremely fast, Rust-backed linter and formatter. By consolidating rules from flake8, black, isort, autoflake, and more, `ruff` keeps code formatting simple and clean with sub-millisecond execution times. |
| **`mypy`** | Type Checking | Enforces strict static type checking to intercept type mismatch bugs before the code is executed or published. |
| **`pytest`** | Test Runner | The industry standard for Python unit testing. Simple to write, highly extensible, and compatible with complex test scenarios. |
| **`pre-commit`** | Git Commit Hooks | Runs linting, formatting, and type-checks locally on staged files to ensure developer code satisfies standard requirements before pushing to remote branches. |

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/aryanp160/aegis.git
cd aegis

# Install using uv (recommended)
uv sync --all-groups

# Or install using standard pip
pip install -e .[dev,test]
```

---

## 📖 CLI Usage

Aegis provides a command-line interface:

```bash
# Display general help
aegis --help

# Display the version of Aegis
aegis version
```

---

## 🤝 Contributing

We welcome contributions! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before submitting pull requests.

## 📄 License

Distributed under the Apache-2.0 License. See [LICENSE](LICENSE) for details.
