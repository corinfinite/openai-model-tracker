# openai-model-tracker

To get started, run the following:

```
poetry install
poetry run openai-model-tracker
```

# Formating & type checking
```
poetry run black openai-model-tracker
poetry run mypy openai-model-tracker
```

# Nix Support
This project comes with nix support. You can enter the nix shell by running `nix develop`.

## Building
Building can help troubleshoot packaging issues. Run `nix build` and then `results/bin/openai-model-tracker`.
