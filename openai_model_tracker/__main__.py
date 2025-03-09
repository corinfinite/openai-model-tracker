"""OpenAI Model Tracker - Track new models as they are released."""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Set, Optional

import requests
import tabulate
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_openai_models() -> Dict[str, Any]:
    """Query the OpenAI API for available models."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")

    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get("https://api.openai.com/v1/models", headers=headers)
    if response.status_code != 200:
        raise Exception(
            f"Error fetching models: {response.status_code} - {response.text}"
        )

    result: Dict[str, Any] = response.json()
    return result


def load_config(config_path: str = "openai_models.json") -> Dict[str, List[Dict[str, Any]]]:
    """Load the existing configuration file or create a new one if it doesn't exist."""
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            result: Dict[str, List[Dict[str, Any]]] = json.load(f)
            return result
    return {"models": []}


def save_config(
    config: Dict[str, List[Dict[str, Any]]], config_path: str = "openai_models.json"
) -> None:
    """Save the updated configuration to file."""
    # Sort models by api_created date (oldest first)
    config["models"] = sorted(config["models"], key=lambda x: x["api_created"])

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def check_for_new_models() -> List[Dict[str, Any]]:
    """Check for new models but don't update the config file.

    Returns:
        list: A list of new models found. Empty list if no new models found.
    """
    try:
        # Get models from API
        api_response = get_openai_models()

        # Load existing config
        config = load_config()

        # Create a set of existing model IDs for efficient lookup
        existing_model_ids: Set[str] = {model["id"] for model in config["models"]}

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

        return new_models

    except Exception as e:
        print(f"Error: {str(e)}")
        return []


def update_models_config() -> None:
    """Check for new models and update the config file."""
    try:
        new_models = check_for_new_models()

        if not new_models:
            return

        # Load config again to ensure we have the latest
        config = load_config()

        # Add new models to config
        for model in new_models:
            config["models"].append(model)

        # Save updated config
        save_config(config)
        print(f"Added {len(new_models)} new models to the config file.")

    except Exception as e:
        print(f"Error updating models: {str(e)}")


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


def main() -> None:
    """Main entry point for the application."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "list":
            print_models_table()
        elif command == "update":
            update_models_config()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: list, update")
    else:
        # Default behavior is now to only check, not modify
        new_models = check_for_new_models()
        if new_models:
            sys.exit(1)


if __name__ == "__main__":
    main()
