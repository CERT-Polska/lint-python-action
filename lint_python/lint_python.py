import argparse
import logging
import pathlib
import subprocess
import sys
from typing import List, Optional, TypedDict, cast

import toml
import yaml

from .constants import USED_LINTERS, __version__

LintPythonConfig = TypedDict(
    "LintPythonConfig",
    {
        "source": str,
        "lint-version": Optional[str],
        "use-isort": Optional[bool],
        "use-black": Optional[bool],
        "use-flake8": Optional[bool],
        "use-mypy": Optional[bool],
        "extra-requirements": Optional[str],
    },
)

LintGithubActionStep = TypedDict(
    "LintGithubActionStep", {"uses": str, "with": LintPythonConfig}
)


def discover_toml_config() -> Optional[LintPythonConfig]:
    pyproject_path = pathlib.Path("./pyproject.toml")

    if not pyproject_path.exists():
        return None

    try:
        with pyproject_path.open("r") as f:
            pyproject_tools = toml.load(f).get("tool", {})
    except Exception:
        logging.exception("Unable to parse pyproject.toml file.")

    if "lint-python" in pyproject_tools:
        return pyproject_tools["lint-python"]
    return None


def discover_github_action_step() -> Optional[LintGithubActionStep]:
    workflows_path = pathlib.Path(".github/workflows")
    if not workflows_path.exists():
        return None

    for yml_file in workflows_path.glob("*.yml"):
        try:
            with yml_file.open("r") as f:
                workflow_spec = yaml.safe_load(f)
                for job, job_spec in workflow_spec["jobs"].items():
                    for step in job_spec.get("steps", []):
                        if step.get("uses").startswith(
                            "CERT-Polska/lint-python-action"
                        ):
                            return step
        except Exception:
            logging.exception(f"Unable to parse {str(yml_file)}.")
    return None


def discover_config() -> Optional[LintPythonConfig]:
    if config := discover_toml_config():
        return config
    if step := discover_github_action_step():
        config = cast(LintPythonConfig, dict(step["with"]))
        if "@v" in step["uses"]:
            config["lint-version"] = step["uses"].split("@v")[1]
        return config
    return None


def run_command(module: str, args: List[str]) -> None:
    """
    Run linter using `python -m` to force using package installed in virtualenv.
    In case package is not installed, it will fail instead of propagating
    to global package. This should be less confusing and most Python CLI tools
    are implementing `__main__.py` entrypoint.
    """
    logging.debug(f"Running command {args}")
    subprocess.run(
        args=[sys.executable, "-m", module, *args],
        check=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def perform_linting(config: LintPythonConfig, check_only: bool) -> None:
    def run_tool(command: str, *args: str, check: bool = False) -> None:
        logging.info(f"Linting with {command}")
        run_command(command, [*args, *(["--check"] if check else []), config["source"]])

    if config.get("use-isort", True):
        run_tool("isort", check=check_only)
    if config.get("use-black", True):
        run_tool("black", check=check_only)
    if config.get("use-flake8", True):
        run_tool("flake8")
    if config.get("use-mypy", True):
        run_tool("mypy")


def perform_pip_install(config: LintPythonConfig, with_extra: bool) -> None:
    requirements = list(USED_LINTERS)
    if with_extra:
        requirements += (config.get("extra-requirements") or "").split()
    run_command("pip", ["install", "-U", *requirements])


def validate_config(config: LintPythonConfig) -> bool:
    if "source" not in config:
        logging.error("'source' is required field in lint-python configuration.")
        return False

    if "lint-version" not in config:
        logging.warning(
            "Required lint-python version is unspecified. It's recommended to specify "
            "at least major required version in case of breaking changes."
        )
        return True

    lint_version = cast(str, config["lint-version"])
    if "." not in lint_version:
        lint_version += "."

    logging.debug(f"Required version: {lint_version}")

    if not __version__.startswith(lint_version):
        logging.error(
            f"Version mismatch: installed lint-python is v{__version__} but "
            f"v{lint_version} is required by project."
        )
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint the source code.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Perform only check and don't modify the files",
    )
    parser.add_argument(
        "--install", action="store_true", help="Install required linters before linting"
    )
    parser.add_argument(
        "--install-only",
        action="store_true",
        help="Install required linters but don't perform linting",
    )
    parser.add_argument(
        "--no-extras",
        action="store_false",
        dest="with_extras",
        help="Omit extra-requirements during installation",
    )
    args = parser.parse_args()

    logging.basicConfig(level=(logging.DEBUG if args.debug else logging.INFO))

    lint_config = discover_config()
    if not lint_config:
        logging.error(
            "lint-python configuration not discovered in project. "
            "Are you in project root directory?"
        )
        sys.exit(1)

    if not validate_config(lint_config):
        logging.error("lint-python configuration not validated correctly.")
        sys.exit(1)

    try:
        if args.install or args.install_only:
            perform_pip_install(lint_config, args.with_extras)
        if not args.install_only:
            perform_linting(lint_config, args.check)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command {e.args} failed with return code {e.returncode}")
        sys.exit(1)
