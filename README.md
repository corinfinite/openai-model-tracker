# openai-model-tracker

To get started, run the following:

```
poetry install
poetry run openai-model-tracker
```

## Usage

- Run without arguments to check for and add new OpenAI models:
  ```
  poetry run openai-model-tracker
  ```

- Run with the `list` argument to display a table of all tracked models:
  ```
  poetry run openai-model-tracker list
  ```
  This will show all models sorted by creation date in a formatted table.

# Formating & type checking
```
poetry run black openai-model-tracker
poetry run mypy openai-model-tracker
```

# Nix Support
This project comes with nix support. You can enter the nix shell by running `nix develop`.

## Building
Building can help troubleshoot packaging issues. Run `nix build` and then `results/bin/openai-model-tracker`.
