import argparse
import logging
import pathlib
import subprocess
import sys
from typing import Optional, TypedDict

from yaml import safe_load

LintActionConfig = TypedDict(
    "LintActionConfig",
    {
        "source": str,
        "python-version": Optional[str],
        "use-isort": Optional[bool],
        "use-black": Optional[bool],
        "use-flake8": Optional[bool],
        "use-mypy": Optional[bool],
        "install-requirements": Optional[bool],
        "extra-requirements": Optional[str],
    },
)

LintActionStep = TypedDict("LintActionStep", {"uses": str, "with": LintActionConfig})


class WorkflowDiscoverError(Exception):
    pass


def discover_action() -> LintActionStep:
    workflows_path = pathlib.Path(".github/workflows")
    if not workflows_path.exists():
        raise WorkflowDiscoverError(
            "Can't find .github/workflows. Are you in project root?"
        )

    for yml_file in workflows_path.glob("*.yml"):
        try:
            with yml_file.open("r") as f:
                workflow_spec = safe_load(f)
                for job, job_spec in workflow_spec["jobs"].items():
                    for step in job_spec.get("steps", []):
                        if step.get("uses").startswith(
                            "CERT-Polska/lint-python-action"
                        ):
                            return step
        except Exception:
            logging.warning(f"Unable to parse {str(yml_file)}.")
    raise WorkflowDiscoverError(
        "Can't find lint-python-action workflow. Is it used by project?"
    )


def run_command(args):
    logging.debug(f"Running command {args}")
    subprocess.run(args=args, check=True, stdout=sys.stdout, stderr=sys.stderr)


def perform_linting(action: LintActionConfig, check_only=True):
    def run_tool(command, *args, check=False):
        logging.info(f"Linting with {command}")
        run_command(
            [
                "python3",
                "-m",
                command,
                *args,
                *(["--check"] if check else []),
                action["source"],
            ]
        )

    if action.get("use-isort", True):
        run_tool("isort", check=check_only)
    if action.get("use-black", True):
        run_tool("black", check=check_only)
    if action.get("use-flake8", True):
        run_tool("flake8")
    if action.get("use-mypy", True):
        run_tool("mypy", "--namespace-packages")


def perform_pip_install(action: LintActionConfig, with_extra: bool):
    requirements = ["isort==5.10.1", "black==22.3.0", "flake8==3.8.4", "mypy==0.940"]
    if with_extra:
        requirements += (action.get("extra-requirements") or "").split()
    run_command(["python3", "-m", "pip", "install", "-U", *requirements])


def main():
    parser = argparse.ArgumentParser(description="Lint the source code.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Perform only check and don't modify the files",
    )
    parser.add_argument(
        "--install", action="store_true", help="Install required linters"
    )
    parser.add_argument(
        "--no-extras",
        action="store_false",
        dest="with_extras",
        help="Omit extra-requirements during installation",
    )
    args = parser.parse_args()

    logging.basicConfig(level=(logging.DEBUG if args.debug else logging.INFO))

    try:
        lint_action = discover_action()["with"]
        if args.install:
            perform_pip_install(lint_action, args.with_extras)
        perform_linting(lint_action, args.check)
    except WorkflowDiscoverError:
        logging.exception("Could not detect lint-python-action workflow in project")
    except subprocess.CalledProcessError as e:
        logging.error(f"Command {e.args} failed with return code {e.returncode}")
