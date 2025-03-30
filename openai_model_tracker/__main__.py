"""OpenAI Model Tracker - Track new models as they are released."""

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

# Verbose output for CI environments
VERBOSE = os.getenv("OPENAI_MODEL_TRACKER_VERBOSE", "").lower() in ("1", "true", "yes")


def log_verbose(message: str) -> None:
    """Log message if verbose mode is enabled."""
    if VERBOSE:
        print(f"DEBUG: {message}")


def get_openai_models() -> Dict[str, Any]:
    """Query the OpenAI API for available models."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set or empty")

    if api_key.startswith("sk-") is False:
        raise ValueError(
            "OPENAI_API_KEY appears to be invalid (should start with 'sk-')"
        )

    log_verbose(f"Sending request to OpenAI API")
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
    log_verbose(f"Retrieved {len(result.get('data', []))} models from API")
    return result


def load_config(config_path: str = CONFIG_PATH) -> Dict[str, List[Dict[str, Any]]]:
    """Load the existing configuration file or create a new one if it doesn't exist."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                result: Dict[str, List[Dict[str, Any]]] = json.load(f)
                log_verbose(
                    f"Loaded {len(result.get('models', []))} models from config"
                )
                return result
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in config file: {str(e)}")
        except Exception as e:
            raise Exception(f"Error loading config file: {str(e)}")

    log_verbose(f"Config file not found, creating empty config")
    return {"models": []}


def save_config(
    config: Dict[str, List[Dict[str, Any]]], config_path: str = CONFIG_PATH
) -> None:
    """Save the updated configuration to file."""
    # Sort models by api_created date (oldest first)
    config["models"] = sorted(config["models"], key=lambda x: x["api_created"])
    log_verbose(f"Saving {len(config['models'])} models to config file")

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        raise Exception(f"Error saving config file: {str(e)}")


def check_for_new_models() -> Tuple[List[Dict[str, Any]], bool]:
    """Check for new models but don't update the config file.

    Returns:
        tuple: A tuple containing:
            - A list of new models found
            - A boolean indicating if there was an error
    """
    error_occurred = False
    try:
        # Get models from API
        log_verbose("Starting check for new models")
        api_response = get_openai_models()

        # Load existing config
        config = load_config()

        # Create a set of existing model IDs for efficient lookup
        existing_model_ids: Set[str] = {model["id"] for model in config["models"]}
        log_verbose(f"Found {len(existing_model_ids)} existing models in config")

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

        if VERBOSE:
            print("\nDetailed error information:")
            traceback.print_exc()

        return [], True


def update_models_config() -> bool:
    """Check for new models and update the config file.

    Returns:
        bool: True if updates were made, False otherwise
    """
    try:
        new_models, error = check_for_new_models()

        if error:
            print(
                "Error occurred during check for new models. Cannot proceed with update."
            )
            return False

        if not new_models:
            return False

        # Load config again to ensure we have the latest
        config = load_config()

        # Add new models to config
        for model in new_models:
            config["models"].append(model)

        # Save updated config
        save_config(config)
        print(f"Added {len(new_models)} new models to the config file.")
        return True

    except Exception as e:
        print(f"Error updating models: {str(e)}")

        if VERBOSE:
            print("\nDetailed error information:")
            traceback.print_exc()

        return False


def print_models_table() -> None:
    """Pretty print the models from the config file in a table format."""
    try:
        # Load config
        config = load_config()

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

        if VERBOSE:
            print("\nDetailed error information:")
            traceback.print_exc()


def main() -> None:
    """Main entry point for the application."""
    try:
        if len(sys.argv) > 1:
            command = sys.argv[1]
            if command == "list":
                print_models_table()
            elif command == "update":
                updated = update_models_config()
                # Exit with 0 if updated successfully or no updates needed
                # Exit with 1 if there was an error updating
                sys.exit(0 if updated or not updated else 1)
            elif command == "check-and-update":
                # Combined command for CI environments
                new_models, error = check_for_new_models()
                if error:
                    sys.exit(2)  # Exit with code 2 for API errors

                if new_models:
                    # Load config again to ensure we have the latest
                    config = load_config()

                    # Add new models to config
                    for model in new_models:
                        config["models"].append(model)

                    # Save updated config
                    save_config(config)
                    print(f"Added {len(new_models)} new models to the config file.")
                    sys.exit(0)  # Successfully updated
                else:
                    print("No updates needed.")
                    sys.exit(0)  # No updates needed
            else:
                print(f"Unknown command: {command}")
                print("Available commands: list, update, check-and-update")
                sys.exit(1)
        else:
            # Default behavior is now to only check, not modify
            new_models, error = check_for_new_models()
            if error:
                sys.exit(2)  # Exit with code 2 for API errors
            if new_models:
                sys.exit(1)  # Exit with code 1 if new models found
            sys.exit(0)  # Exit with code 0 if no new models found
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        if VERBOSE:
            traceback.print_exc()
        sys.exit(3)  # Exit with code 3 for unexpected errors


if __name__ == "__main__":
    main()
