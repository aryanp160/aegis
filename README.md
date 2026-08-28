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

### Using `uv` (recommended)
```bash
# Clone the repository
git clone https://github.com/aryanp160/aegis.git
cd aegis

# Install environment and sync all dependency groups
uv sync --all-groups
```

### Using standard `pip`
```bash
pip install -e .[dev,test]
```

---

## 🚦 Quick Start

### SQL Parser API
Aegis provides a type-safe Python API for SQL migration discovery, loading, validation, and parsing.

#### 1. Standard Parsing
```python
from pathlib import Path
from aegis.parser import parse, parse_directory

# Parse a single SQL migration file
result = parse(Path("examples/postgres/0001_init.sql"))
if result.success and result.migration:
    print(f"Dialect: {result.migration.dialect}")
    print(f"SQL statements count: {len(result.migration.statements)}")
    # Access the sqlglot AST nodes
    for ast_node in result.migration.ast_nodes:
        print(type(ast_node))
else:
    print(f"Errors occurred: {result.errors}")

# Parse an entire migration directory recursively
results = parse_directory(Path("examples/"))
for res in results:
    if res.success and res.migration:
        print(f"Parsed {res.migration.path.name}")
```

#### 2. Advanced Diagnostic Validation Error Handling
The parser isolates validation errors (empty files, comments-only files, unreadable files) and syntax compilation diagnostics (including line and column numbers).

```python
from pathlib import Path
from aegis.parser import SqlParser

parser = SqlParser(use_cache=True)

# Parse a file containing syntax errors
result = parser.parse(Path("tests/bad_migration.sql"))
if not result.success:
    print("Parsing Failed!")
    for error in result.errors:
        # Will output line and column information if available:
        # e.g., "SQL syntax compile failure:
        # Line 1, Col 14: Expected table name..."
        print(error)
```

#### 3. Rule Engine Analysis
Once a migration is parsed, you can evaluate it against Aegis's core static analysis rules to identify potentially unsafe operations.

```python
from pathlib import Path
from aegis import RuleEngine
from aegis.parser import SqlParser

# Parse migration
parser = SqlParser()
result = parser.parse(Path("examples/postgres/0001_init.sql"))

if result.success and result.migration:
    engine = RuleEngine()
    analysis = engine.analyze([result.migration])

    print(
        f"Discovered {len(analysis.violations)} violations in {analysis.duration_ms:.2f}ms"
    )
    for violation in analysis.violations:
        print(
            f"[{violation.severity.upper()}] {violation.code} on line {violation.line}: {violation.message}"
        )
```

---

## 💻 CLI Usage

Aegis provides a command-line interface to lint migrations, inspect rules, and display documentation.

### 1. Lint SQL Migrations
Lint files or directories for rule violations.
```bash
# Lint a single SQL migration file
aegis lint migration.sql

# Lint a directory containing migrations
aegis lint migrations/

# Run lint and return structured JSON output
aegis lint migrations/ --format json

# Filter violations by minimum severity
aegis lint migrations/ --severity error

# Ignore specific rule IDs
aegis lint migrations/ --ignore AEG-101,AEG-107

# Exclude specific files/directories from linting
aegis lint migrations/ --exclude migrations/ignored_dir/
```

### 2. List Registered Rules Catalog
View all active static analysis rules or filter by category or severity.
```bash
# List all registered rules
aegis rules

# Filter rules by category
aegis rules --category destructive

# Filter rules by severity level
aegis rules --severity error
```

### 3. Explain Rules
Get detailed documentation, risk assessment, and remediation steps for specific rules.
```bash
aegis explain AEG-101
aegis explain allow_drop_table
```

### 4. Check CLI Version & Environment
```bash
aegis version
# or
aegis --version
```

### 5. Shell Completion
Generate and configure shell completion scripts for your active shell environment.

#### Generate Completion Scripts
Generate raw completion scripts for Bash, Zsh, or Fish:
```bash
# Bash
aegis completion bash > aegis.bash

# Zsh
aegis completion zsh > aegis.zsh

# Fish
aegis completion fish > aegis.fish
```

#### Install Shell Completion
##### Zsh (Recommended)
1. Generate the completion script and save it to a folder in your `$fpath`:
   ```bash
   aegis completion zsh > ~/.zsh/completion/_aegis
   ```
2. Make sure the folder is added to your `~/.zshrc` before calling `compinit`:
   ```zsh
   fpath=(~/.zsh/completion $fpath)
   autoload -Uz compinit && compinit
   ```
3. Restart your shell or run `source ~/.zshrc` to activate the completion menu.

##### Bash
1. Output the completion script to a directory and source it in your `~/.bashrc`:
   ```bash
   aegis completion bash > ~/.aegis-completion.bash
   echo "source ~/.aegis-completion.bash" >> ~/.bashrc
   ```
2. Reload your shell configuration.

##### Fish
1. Save the completion script directly to the Fish completions directory:
   ```bash
   aegis completion fish > ~/.config/fish/completions/aegis.fish
   ```
2. Fish will dynamically load it in your next session.

---

## ⚡ Performance Benchmarks
To run performance latency and throughput benchmarks for the SQL Parser core and Rule Engine:
```bash
python benchmarks/benchmark_parser.py
python scripts/benchmark_engine.py
```

---

## 🗺️ Roadmap

* **v0.2.0-alpha.2** (Completed):
  - Added granular exceptions (`EmptySQLFileError`, `UnreadableFileError`).
  - Added line and column diagnostic compilation on SQL syntax errors.
  - Optimized file scanner traversing folders without redundant resolution checks.
  - Added optional AST caching to improve parsing latency.
* **v0.3.0-alpha.1** (Completed):
  - Setup core static analyzer Rule Engine and severity mapping.
  - Extensible `ASTVisitor` pattern for custom rule authoring.
  - Deterministic evaluation sorting.
  - Fully documented rules (`docs/rules/`).
* **v0.3.0-alpha.2** (Completed):
  - Rule suppression using `aegis.toml` config file.
  - Per-rule/per-file overrides and severity customization.
  - Rich visual terminal diagnostics with caret SQL syntax pointing.
  - Enhanced PostgreSQL rule coverage and Golden SQL test suite.
  - Engine execution and AST visitor caching optimizations.
* **v0.4.0-beta.1** (Completed):
  - Deliver command-line commands `aegis lint` and `aegis explain` rendering diagnostics using `rich` console formatting.
  - Introduce production-ready CLI.
* **v0.4.0-beta.2** (Current Release):
  - CLI UX improvements: enhanced command descriptions, structured `--help` output with examples, argument/option descriptions, Rich version panel, and `aegis rules` discovery command.

---

## 🤝 Contributing

We welcome contributions from the community! Before submitting pull requests, please read our [CONTRIBUTING.md](CONTRIBUTING.md) to understand branch naming conventions, Conventional Commit formatting, and development loop setup instructions.

Please also review our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community guidelines.

## 📄 License

Distributed under the Apache-2.0 License. See [LICENSE](LICENSE) for details.
