# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0-alpha.1] - 2026-07-05

### Added
- Dialect-aware SQL Parser core package `src/aegis/parser/`.
- Convenient public helper APIs `parse` and `parse_directory`.
- Heuristic dialect detection support for `postgresql` and `mysql` schemas.
- `sqlglot` AST compilers translating SQL content strings to Expression arrays.
- Pydantic models `ParsedMigration` and `ParseResult` to map parser results.
- `SQLDialect` StrEnum defining supported migration dialects.
- Custom structured exception classes inheriting from `ParserError`.
- Safe recursive file scanner ignoring python cache files, hidden files, and circular symlinks.
- SQL parsing performance benchmarking script `benchmarks/benchmark_parser.py`.
- Parser architecture layout documentation `docs/architecture.md`.

## [0.1.0-alpha.1] - 2026-07-04

### Added
- Bootstrap repository structure with placeholder `.gitkeep` files in `docs/`, `examples/`, `benchmarks/`, and `scripts/`.
- Repository developer configurations including `.gitignore`, `.editorconfig`, and `.pre-commit-config.yaml`.
- Core python package metadata configuration in `pyproject.toml` using modern dependency definitions.
- CLI application scaffold using Typer and Rich console formatting.
- Config loader skeleton validating parameters using Pydantic schemas.
- Global console logging handler leveraging RichHandler formats.
- Complete unit test suite verifying CLI exit codes, logging outputs, and TOML config structures.
- GitHub Actions CI workflows for automated testing, CodeQL security scanning, and package tag release builds.
- Initial community guidelines: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, and `CHANGELOG.md`.
