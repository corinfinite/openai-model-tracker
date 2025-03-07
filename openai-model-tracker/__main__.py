import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
import tabulate

# Load environment variables from .env file
load_dotenv()

def get_openai_models():
    """Query the OpenAI API for available models."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    response = requests.get("https://api.openai.com/v1/models", headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error fetching models: {response.status_code} - {response.text}")
    
    return response.json()

def load_config(config_path="openai_models.json"):
    """Load the existing configuration file or create a new one if it doesn't exist."""
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {"models": []}

def save_config(config, config_path="openai_models.json"):
    """Save the updated configuration to file."""
    # Sort models by api_created date (oldest first)
    config["models"] = sorted(config["models"], key=lambda x: x["api_created"])
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

def check_for_new_models():
    """Check for new models and update config file."""
    try:
        # Get models from API
        api_response = get_openai_models()
        
        # Load existing config
        config = load_config()
        
        # Create a set of existing model IDs for efficient lookup
        existing_model_ids = {model["id"] for model in config["models"]}
        
        # Check for new models
        new_models_count = 0
        for model in api_response["data"]:
            if model["id"] not in existing_model_ids:
                # This is a new model
                new_models_count += 1
                model_date = datetime.fromtimestamp(model["created"]).strftime("%Y-%m-%d %H:%M:%S")
                print(f"New model discovered: {model['id']} (created: {model_date})")
                
                # Add to our config
                config["models"].append({
                    "id": model["id"],
                    "api_created": model["created"]
                })
        
        # Save updated config if we found new models
        if new_models_count > 0:
            save_config(config)
            print(f"Added {new_models_count} new models to the config file.")
        else:
            print("No new models found.")
            
    except Exception as e:
        print(f"Error: {str(e)}")

def print_models_table():
    """Pretty print the models from the config file in a table format."""
    try:
        # Load config
        config = load_config()
        
        if not config["models"]:
            print("No models found in the config file.")
            return
        
        # Prepare table data
        table_data = []
        for model in sorted(config["models"], key=lambda x: x["api_created"]):
            # Convert timestamp to human readable date
            created_date = datetime.fromtimestamp(model["api_created"]).strftime("%Y-%m-%d %H:%M:%S")
            table_data.append([model["id"], created_date])
        
        # Print table
        headers = ["Model ID", "Created Date"]
        print(tabulate.tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"\nTotal models: {len(config['models'])}")
        
    except Exception as e:
        print(f"Error printing models table: {str(e)}")

def main():
    """Main entry point for the application."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print_models_table()
    else:
        check_for_new_models()

if __name__ == "__main__":
    main()