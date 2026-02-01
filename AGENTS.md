# AI Agent Collaboration Guidelines

This document provides guidelines for AI agents (GitHub Copilot, Claude, etc.) working on this repository to ensure consistent, high-quality contributions that align with the project maintainer's expectations.

## Table of Contents

- [Commit Message Format](#commit-message-format)
- [Code Change Philosophy](#code-change-philosophy)
- [Testing Requirements](#testing-requirements)
- [Code Quality Standards](#code-quality-standards)
- [General Guidelines](#general-guidelines)

---

## Commit Message Format

**Always use Conventional Commits format with emoji icons**, following semantic-release conventions:

### Format

```
<type>: <emoji> <description>

[optional body]

[optional footer]
```

### Types and Icons

| Type | Icon | Description | Example |
|------|------|-------------|---------|
| `feat` | ✨ | New feature | `feat: ✨ Add streaming mode support` |
| `fix` | 🐛 | Bug fix | `fix: 🐛 Correct LinkedIn Article field extraction` |
| `docs` | 📝 | Documentation changes | `docs: 📝 Update README with streaming mode` |
| `test` | ✅ | Test additions/changes | `test: ✅ Add LinkedIn comment extraction tests` |
| `refactor` | ♻️ | Code refactoring | `refactor: ♻️ Extract metadata parsing logic` |
| `perf` | ⚡ | Performance improvements | `perf: ⚡ Optimize batch processing` |
| `chore` | 🔧 | Maintenance tasks | `chore: 🔧 Update dependencies` |
| `ci` | 👷 | CI/CD changes | `ci: 👷 Add GitHub Actions workflow` |
| `style` | 💄 | Code style/formatting | `style: 💄 Format with black` |
| `build` | 📦 | Build system changes | `build: 📦 Update Pipfile` |

### Examples

```
fix: 🐛 Correct Article title extraction from 'headline' to 'name' field

LinkedIn Articles use 'name' for the actual title and 'headline' for 
the opening paragraph. Updated extraction logic to prioritize 'name'.

Fixes #42
```

```
feat: ✨ Add offline-first test mode with local fixtures

- Support loading HTML from local fixture files
- Fall back to live download if fixture missing
- Show [LOCAL] or [LIVE] indicator in test output

Closes #38
```

---

## Code Change Philosophy

### Conservative Changes - ALWAYS

**Principle: Make the smallest possible changes to achieve the goal.**

#### Do's ✅

- **Minimal modifications**: Change as few lines as possible
- **Surgical precision**: Target exact problem areas only
- **Preserve working code**: Never delete/modify working functionality unless absolutely necessary
- **Follow existing patterns**: Match the codebase's existing style and structure
- **Simple and direct**: Avoid unnecessary abstractions
- **Short and precise**: Keep solutions concise

#### Don'ts ❌

- **No refactoring** unless explicitly requested or fixing a security issue
- **No additional files** unless specifically required (helper scripts, workarounds, etc.)
- **No unrelated fixes**: Ignore unrelated bugs/tests - not your responsibility
- **No new dependencies** unless absolutely necessary
- **No breaking changes** to existing behavior (except for security fixes)
- **No over-engineering**: Resist the urge to "improve" working code

### Example Scenarios

**Good** 🟢:
```python
# Change one line to fix field extraction
metadata["title"] = target_item.get("name", target_item.get("headline", ""))
```

**Bad** 🔴:
```python
# Don't create a whole new abstraction layer
class MetadataExtractor:
    def __init__(self, config):
        self.field_priority = config.get_field_priority()
    
    def extract_title(self, item):
        for field in self.field_priority:
            if value := item.get(field):
                return value
```

---

## Testing Requirements

### Before Making Changes

1. **Run existing tests** to understand baseline
2. **Identify related tests** that might be affected
3. **Note any pre-existing failures** (not your responsibility to fix)

### After Making Changes

1. **Run affected tests first** (targeted testing)
2. **Verify no regressions** on passing tests
3. **Run full test suite** only when changes are complete
4. **Manual verification** for user-facing changes

### Test Updates

- **Update test expectations** when fixtures/data change
- **Preserve Unicode characters** (use `allow_unicode=True` in YAML)
- **Match exact output** including special characters (', ", …, etc.)
- **Do not modify unrelated tests** - this could hide bugs

### Running Tests

```bash
# Run all tests
make test

# Or directly
python src/main.py --test-yaml
```

---

## Code Quality Standards

### Formatting and Linting

**Always format and lint before committing:**

```bash
# Format with black
make format

# Lint with ruff
make lint

# Or do both
make check
```

### Code Style

- **Follow PEP 8** conventions
- **Use type hints** where helpful
- **Write docstrings** for functions (match existing style)
- **Preserve existing style** in modified files
- **Don't add comments** unless they match existing comment style or explain complex logic

### Unicode and Special Characters

- **Preserve special characters**: curly quotes ('), apostrophes ('), ellipses (…)
- **Use UTF-8 encoding**: Always specify `encoding='utf-8'` when reading/writing files
- **YAML handling**: Use `allow_unicode=True` when dumping YAML
- **Test string matching**: Be aware of Unicode character differences

Example:
```python
# Correct ✅
with open('file.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

# Wrong ❌
with open('file.yaml', 'w') as f:  # Missing encoding
    yaml.dump(data, f)  # Will corrupt Unicode characters
```

---

## General Guidelines

### Communication

- **Report progress frequently** using the `report_progress` tool
- **Commit incrementally** after each verified change
- **Use checklists** in PR descriptions to track progress
- **Be explicit** about what changed and why

### Problem Solving

1. **Understand the issue** fully before coding
2. **Explore the codebase** to understand context
3. **Plan minimal changes** (use report_progress to outline)
4. **Implement incrementally** with verification at each step
5. **Test thoroughly** before finalizing

### Security

- **Run security scans**: Use `codeql_checker` tool before finalizing
- **Fix discovered vulnerabilities** that are related to your changes
- **Document security findings** in a Security Summary
- **Don't introduce new vulnerabilities**

### When in Doubt

- **Ask for clarification** rather than making assumptions
- **Propose solutions** before implementing large changes
- **Default to conservative** - less is more
- **Preserve existing behavior** unless explicitly changing it

---

## Workflow Checklist

Use this checklist for every contribution:

- [ ] Understand the issue/requirement fully
- [ ] Explore relevant code and tests
- [ ] Plan minimal changes (use `report_progress`)
- [ ] Make changes incrementally
- [ ] Run affected tests after each change
- [ ] Format code with `make format`
- [ ] Lint code with `make lint`
- [ ] Run full test suite
- [ ] Verify no regressions
- [ ] Use semantic commit message with icon
- [ ] Report progress with clear description
- [ ] Review committed files (exclude build artifacts)

---

## Tools and Commands

### Make Commands

```bash
make install    # Install dependencies
make test       # Run tests
make format     # Format code with black
make lint       # Lint with ruff
make check      # Format + lint + test
make clean      # Clean build artifacts
```

### Git Operations

All git commits/pushes are handled by the `report_progress` tool - **do not use git commands directly** in the CLI.

---

## Examples of Good Contributions

### Example 1: Bug Fix

**Commit**: `fix: 🐛 Correct LinkedIn Article title extraction`

**Changes**:
- Modified 1 line in `src/main.py`
- Changed field priority from `headline` to `name`
- Fixed 2 failing tests

**Why it's good**:
- Minimal change (1 line)
- Clear problem and solution
- Proper semantic commit message

### Example 2: Test Update

**Commit**: `test: ✅ Update test expectations to match current fixtures`

**Changes**:
- Updated 3 test expectations in `tests/data.yaml`
- Preserved Unicode characters
- No code changes needed

**Why it's good**:
- Surgical fix to test data only
- Preserved special characters correctly
- Clear documentation of what changed

---

## Anti-Patterns to Avoid

### ❌ Over-Engineering

Don't create abstractions when a simple change suffices:

```python
# Bad - unnecessary abstraction
class FieldExtractor:
    # 50 lines of abstraction for a one-line fix
```

### ❌ Scope Creep

Don't fix unrelated issues in the same commit:

```python
# Bad - mixing concerns
- Fix LinkedIn Article extraction
- Refactor entire metadata module
- Update 10 unrelated tests
- Add new features
```

### ❌ Breaking Changes

Don't change working behavior without explicit permission:

```python
# Bad - changing working API
def extract_metadata(html, url, new_param=None):  # Don't add params
```

---

## Questions?

When working on this repository:

1. **Follow these guidelines strictly**
2. **When in doubt, ask** - don't assume
3. **Make minimal changes** - less is more
4. **Test thoroughly** - verify everything works
5. **Use proper commit format** - semantic with icons

Remember: **The goal is to solve the specific problem with the smallest, safest change possible.**
