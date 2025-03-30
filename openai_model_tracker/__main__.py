"""OpenAI Model Tracker - Track new models as they are released."""

import argparse
import json
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Set, Optional, Tuple

import requests
import tabulate
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration file path
CONFIG_PATH = "openai_models.json"


def log_verbose(message: str, verbose: bool = False) -> None:
    """Log message if verbose mode is enabled."""
    if verbose:
        print(f"DEBUG: {message}")


def get_openai_models(verbose: bool = False) -> Dict[str, Any]:
    """Query the OpenAI API for available models."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set or empty")

    if api_key.startswith("sk-") is False:
        raise ValueError(
            "OPENAI_API_KEY appears to be invalid (should start with 'sk-')"
        )

    log_verbose(f"Sending request to OpenAI API", verbose)
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers=headers,
            timeout=30,  # Add timeout for API request
        )
        response.raise_for_status()  # Raise exception for non-200 responses
    except requests.exceptions.RequestException as e:
        # Enhanced error reporting
        error_message = f"Error accessing OpenAI API: {str(e)}"
        if hasattr(e, "response") and e.response is not None:
            error_message += f"\nStatus code: {e.response.status_code}"
            try:
                error_message += f"\nResponse: {e.response.text}"
            except:
                pass
        raise Exception(error_message)

    result: Dict[str, Any] = response.json()
    log_verbose(f"Retrieved {len(result.get('data', []))} models from API", verbose)
    return result


def load_config(
    config_path: str = CONFIG_PATH, verbose: bool = False
) -> Dict[str, List[Dict[str, Any]]]:
    """Load the existing configuration file or create a new one if it doesn't exist."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                result: Dict[str, List[Dict[str, Any]]] = json.load(f)
                log_verbose(
                    f"Loaded {len(result.get('models', []))} models from config", verbose
                )
                return result
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in config file: {str(e)}")
        except Exception as e:
            raise Exception(f"Error loading config file: {str(e)}")

    log_verbose(f"Config file not found, creating empty config", verbose)
    return {"models": []}


def save_config(
    config: Dict[str, List[Dict[str, Any]]],
    config_path: str = CONFIG_PATH,
    verbose: bool = False,
) -> None:
    """Save the updated configuration to file."""
    # Sort models by api_created date (oldest first)
    config["models"] = sorted(config["models"], key=lambda x: x["api_created"])
    log_verbose(f"Saving {len(config['models'])} models to config file", verbose)

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        raise Exception(f"Error saving config file: {str(e)}")


def check_for_new_models(verbose: bool = False) -> Tuple[List[Dict[str, Any]], bool]:
    """Check for new models but don't update the config file.

    Returns:
        tuple: A tuple containing:
            - A list of new models found
            - A boolean indicating if there was an error
    """
    try:
        # Get models from API
        log_verbose("Starting check for new models", verbose)
        api_response = get_openai_models(verbose)

        # Load existing config
        config = load_config(verbose=verbose)

        # Create a set of existing model IDs for efficient lookup
        existing_model_ids: Set[str] = {model["id"] for model in config["models"]}
        log_verbose(
            f"Found {len(existing_model_ids)} existing models in config", verbose
        )

        # Check for new models
        new_models: List[Dict[str, Any]] = []
        for model in api_response["data"]:
            if model["id"] not in existing_model_ids:
                # This is a new model
                model_date = datetime.fromtimestamp(model["created"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                print(f"New model discovered: {model['id']} (created: {model_date})")
                new_models.append({"id": model["id"], "api_created": model["created"]})

        # Report findings
        if new_models:
            print(
                f"\nFound {len(new_models)} new models that are not in the config file."
            )
            print("Run 'openai_model_tracker update' to add them to the config file.")
        else:
            print("No new models found.")

        return new_models, False

    except Exception as e:
        error_message = f"Error checking for new models: {str(e)}"
        print(error_message)

        if verbose:
            print("\nDetailed error information:")
            traceback.print_exc()

        return [], True


def update_models_config(verbose: bool = False) -> bool:
    """Check for new models and update the config file.

    Returns:
        bool: True if updates were made, False otherwise
    """
    try:
        new_models, error = check_for_new_models(verbose)

        if error:
            print(
                "Error occurred during check for new models. Cannot proceed with update."
            )
            return False

        if not new_models:
            return False

        # Load config again to ensure we have the latest
        config = load_config(verbose=verbose)

        # Add new models to config
        for model in new_models:
            config["models"].append(model)

        # Save updated config
        save_config(config, verbose=verbose)
        print(f"Added {len(new_models)} new models to the config file.")
        return True

    except Exception as e:
        print(f"Error updating models: {str(e)}")

        if verbose:
            print("\nDetailed error information:")
            traceback.print_exc()

        return False


def print_models_table(verbose: bool = False) -> None:
    """Pretty print the models from the config file in a table format."""
    try:
        # Load config
        config = load_config(verbose=verbose)

        if not config["models"]:
            print("No models found in the config file.")
            return

        # Prepare table data
        table_data: List[List[str]] = []
        for model in sorted(config["models"], key=lambda x: x["api_created"]):
            # Convert timestamp to human readable date
            created_date = datetime.fromtimestamp(model["api_created"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            table_data.append([model["id"], created_date])

        # Print table
        headers = ["Model ID", "Created Date"]
        print(tabulate.tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"\nTotal models: {len(config['models'])}")

    except Exception as e:
        print(f"Error printing models table: {str(e)}")

        if verbose:
            print("\nDetailed error information:")
            traceback.print_exc()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Track and monitor new OpenAI models as they become available."
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output for debugging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    subparsers.add_parser("list", help="List all tracked models")

    # Update command
    subparsers.add_parser("update", help="Check for and add new models")

    return parser.parse_args()


def main() -> None:
    """Main entry point for the application."""
    try:
        args = parse_args()
        verbose = args.verbose

        if args.command == "list":
            print_models_table(verbose)
        elif args.command == "update":
            updated = update_models_config(verbose)
            # Exit with 0 if updated successfully or no updates needed
            # Exit with 1 if there was an error updating
            sys.exit(0 if updated or not updated else 1)
        elif args.command is None:
            # Default behavior with no command: check only, don't modify
            new_models, error = check_for_new_models(verbose)
            if error:
                sys.exit(2)  # Exit with code 2 for API errors
            if new_models:
                sys.exit(1)  # Exit with code 1 if new models found
            sys.exit(0)  # Exit with code 0 if no new models found
        else:
            print(f"Unknown command: {args.command}")
            print("Available commands: list, update")
            sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        if "args" in locals() and args.verbose:
            traceback.print_exc()
        sys.exit(3)  # Exit with code 3 for unexpected errors


if __name__ == "__main__":
    main()
