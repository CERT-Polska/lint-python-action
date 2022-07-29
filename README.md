# lint-python-action

Tool that runs common linters on CERT Polska projects written in Python.

Includes [GitHub Actions](https://docs.github.com/en/actions) custom action.

Used linters and auto-formatters are:

```
pip install -U isort==5.10.1 black==22.3.0 flake8==3.8.4 mypy==0.940
```

If you want to introduce these linters into your project, some tools need to be preconfigured to cooperate correctly. 
Check https://black.readthedocs.io/en/stable/guides/using_black_with_other_tools.html for more information.

## Installation

```console
$ pip install lint-python
```

## How to configure lint-python?

Provide configuration in [pyproject.toml](https://peps.python.org/pep-0621/) file.

```toml
[tool.lint-python]
lint-version = "2"
source = "lint_python/" # Put your source directory
extra-requirements = "types-requests"  # Provide additional typing requirements if needed
use-mypy = false  # Turn off any tool you don't want to use
```

If you use Github Actions, you can add it to any steps of the workflow e.g. `.github/workflows/test.yml`

```yaml
name: Test the code
on:
  push:
    branches:
      - master
  pull_request:
    branches:
      - master
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: CERT-Polska/lint-python-action@v2
        with:
          source: karton/
```

Tool can be configured via `with` parameters, but they must be provided directly. 
Don't use any expansion because lint-python tool parses the workflow file on its own.

## How to use it?

```console
$ lint-python
INFO:root:Linting with isort
INFO:root:Linting with black
All done! ✨ 🍰 ✨
3 files left unchanged.
INFO:root:Linting with flake8
INFO:root:Linting with mypy
Success: no issues found in 3 source files
```

If you want to only perform a check without modifying files, use `--check` flag
```console
$ lint-python --check
```

If you want to install packages and tools required for linting, use `--install` flag.
```console
$ lint-python --install
```

## Read more

- https://black.readthedocs.io/en/stable/
- https://black.readthedocs.io/en/stable/guides/using_black_with_other_tools.html
- https://pycqa.github.io/isort/
- https://flake8.pycqa.org/en/latest/
- http://mypy-lang.org/
