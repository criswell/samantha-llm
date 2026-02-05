# GitHub Actions Testing

This directory contains GitHub Actions workflows for automated testing of samantha-llm.

## Workflows

### `tests.yml` - Main Test Suite

Runs on every push and pull request to main branches. Tests are organized into three jobs:

#### 1. **Syntax Validation** (Ubuntu, Python 3.8)
- Validates Python syntax using `py_compile`
- Tests that the script can be executed
- Checks version number format (semver)

#### 2. **Installation Tests** (Multi-OS, Multi-Python)
Tests the samantha-llm script on multiple platforms:
- **Ubuntu**: Python 3.8 (minimum) and 3.12 (latest)
- **macOS**: Python 3.11
- **Windows**: Python 3.11

Each test:
- Makes the script executable (Unix) or runs with Python (Windows)
- Executes `samantha-llm help` to verify basic functionality
- Confirms Python version compatibility

#### 3. **Unit Tests** (Ubuntu, Python 3.11)
- Discovers and runs any `test_*.py` files in the repository
- Note: Tests in `.ai-cerebrum/` are gitignored (user-specific memory)

## Running Tests Locally

### Syntax Check
```bash
python3 -m py_compile samantha-llm
```

### Help Command
```bash
python3 samantha-llm help
```

### Version Check
```bash
python3 -c "import re; content=open('samantha-llm').read(); match=re.search(r'VERSION\s*=\s*[\"']([^\"']+)[\"']', content); print(match.group(1) if match else 'NOT_FOUND')"
```

## What's NOT Tested

The following are intentionally excluded from CI:
- **LLM API calls** - Too expensive and non-deterministic
- **Actual memory generation** - Requires API keys
- **QMD integration** - External dependency
- **Real terminal recordings** - Too slow
- **User-specific `.ai-cerebrum/` files** - Gitignored personal memory

## Test Philosophy

We test the **infrastructure and tooling**, not the AI behavior. The LLM analysis is non-deterministic and expensive, but the file management, CLI, and installation process are all testable and critical to the system working.
