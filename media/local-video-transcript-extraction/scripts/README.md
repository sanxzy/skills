# Local transcript scripts

The public executable is `extract-transcript`. With no explicit destination,
its artifacts are written under
`./.artifacts/transcript/<task_name>/`; the task name defaults to the media
stem or can be supplied with `--task-name`. The Python modules are kept
separate so validation, runtime loading, checkpointing, normalization, and
projection behavior can be tested without a live model.

The wrapper uses `~/.local/models/.venv/bin/python` when available. It never
creates that environment, installs dependencies, downloads a model, or
replaces an existing file. If the environment is absent, the Python command
returns a structured `python_environment_missing` failure.
