# GitHub Copilot Instructions

Welcome! This repository has detailed AI agent collaboration guidelines.

## Primary Documentation

**Please read [AGENTS.md](../AGENTS.md) for complete guidelines** including:

- Commit message format (Conventional Commits with emoji icons)
- Code change philosophy (minimal, conservative changes; avoid unnecessary abstractions)
- Testing requirements
- Code quality standards
- Development workflow

## Quick Reference

### Commit Format
Use Conventional Commits: `<type>: <emoji> <description>`

Examples:
- `feat: ✨ Add new feature`
- `fix: 🐛 Fix bug`
- `docs: 📝 Update documentation`
- `test: ✅ Add tests`

### Core Principles

1. **Make minimal changes** - change as few lines as possible
2. **Preserve working code** - don't refactor unless necessary
3. **Follow existing patterns** - match the codebase style
4. **Test thoroughly** - use `make test`, `make format`, `make lint`
5. **Report progress frequently** - use the report_progress tool

### Development Commands

```bash
make install    # Install dependencies
make test       # Run tests
make format     # Format code with black
make lint       # Lint with ruff
make check      # Format + lint + test
```

### Python Project Details

- Python 3.11+ required
- Uses `pipenv` for dependency management
- Code formatted with `black`
- Linted with `ruff`
- Follows PEP 8 conventions
- UTF-8 encoding with Unicode character preservation

## Full Guidelines

For comprehensive details on all aspects of contributing to this repository, refer to [AGENTS.md](../AGENTS.md).
