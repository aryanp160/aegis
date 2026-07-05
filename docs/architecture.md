# Aegis Architecture Documentation

This document outlines the software design, structure, and pipeline components of the **Aegis** SQL migration static analyzer.

---

## System Design Overview

Aegis is built upon the principles of **Clean Architecture** and **SOLID design patterns**. The codebase is structured to isolate raw SQL loading, parsing, syntax validation, and rule checking.

```
+-------------------------------------------------------------+
|                       CLI Layer                             |
+------------------------------+------------------------------+
                               |
                               v
+------------------------------+------------------------------+
|                     Configuration System                     |
+------------------------------+------------------------------+
                               |
                               v
+------------------------------+------------------------------+
|                     static analyzer (Rules)                 |
+------------------------------+------------------------------+
                               |
                               v
+------------------------------+------------------------------+
|                         Parser Core                         |
+-------------------------------------------------------------+
```

---

## Parser Core Pipeline

The core parser parses raw migration SQL files into structured, dialect-aware `sqlglot` Abstract Syntax Trees (ASTs). The pipeline consists of the following stages:

```
File Discovery
      ↓
Migration Loader (UTF-8, BOM Handling, Pydantic validation)
      ↓
Dialect Detection (PostgreSQL / MySQL checks)
      ↓
sqlglot AST Compiler
      ↓
ParsedMigration Metadata Output
```

### 1. File Discovery
* **File Scans**: Traverses target directories recursively.
* **Filters**: Skips hidden directories (`.*`), Python compilation directories (`__pycache__`), and matches only files with `.sql` suffixes.
* **Symlink Loop Safety**: Resolves absolute canonical paths and maps visited paths to prevent recursive directory lookup cycles.
* **Deterministic Runs**: Discovered file lists are sorted alphabetically to guarantee consistent migration analysis order.

### 2. Migration Loader
* Reads files using `utf-8-sig` encoding, safely stripping Byte Order Mark (BOM) signatures automatically.
* Returns initial metadata validations throwing `InvalidSQLFileError` if files are unreadable, empty, or missing.

### 3. Dialect Detection
* Analyzes file paths and content signatures to identify `postgresql` or `mysql` dialects.
* Ambiguous syntax results in an `UnsupportedDialectError`.

### 4. AST Generator
* Leverages `sqlglot.parse` to compile raw SQL strings into lists of typed `Expression` objects.
* Handles syntax errors by catching `ParseError` and wrapping them in `ParseFailure` results.

---

## Future Rule Engine Integration

In `v0.3.0-alpha.1`, the **Rule Engine** will consume the parsed `ParsedMigration` objects:

1. **AST Node Traverser**: Subclasses of a base rule runner will traverse the `ast_nodes` list (filtering for `exp.Alter`, `exp.Drop`, `exp.ColumnDef`, etc.).
2. **Context Evaluator**: The AST nodes will be checked against the active settings defined in `AegisConfig.rules` (e.g. `allow_drop_column`).
3. **Violations Compiler**: Any destructive or unsafe operations will generate a `Violation` model mapping the file path, triggered warning rule, severity, and resolving guidance.
