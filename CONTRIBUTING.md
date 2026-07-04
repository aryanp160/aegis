# Contributing to Aegis

Thank you for your interest in contributing to Aegis! We want to make contributing to this project as easy and transparent as possible.

## Code of Conduct

By participating in this project, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Development Setup

We use `uv` for python package and dependency management.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/aryanp160/aegis.git
   cd aegis
   ```

2. **Set up the virtual environment and install dependencies**:
   ```bash
   uv sync --all-groups
   ```

3. **Install pre-commit hooks**:
   ```bash
   uv run pre-commit install
   ```

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages. This allows us to automate changelogs and semantic versioning.

Commit messages should follow the structure:
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Allowed Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes that affect the build system or external dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files

### Example

```
feat(cli): add output format flag to verify command

Closes #123
```

## Pull Request Process

1. Create a new branch from `develop`:
   ```bash
   git checkout -b feature/my-amazing-feature develop
   ```
2. Make your changes and commit them following the conventional commit guidelines.
3. Ensure all tests pass and static analysis tools are clean:
   ```bash
   uv run pytest
   uv run mypy src
   uv run ruff check src
   ```
4. Push your branch to GitHub and open a Pull Request against `develop`.
5. Ensure the CI builds pass. One of the maintainers will review your PR as soon as possible.
