# Contributing

Bug reports and pull requests are welcome. Use [GitHub issues](../../issues)
for bugs and feature requests. Include debug logs (see the README) and your
monitor's model.

## Development setup

You need [uv](https://docs.astral.sh/uv/). The dev container installs it for
you.

- `scripts/setup` installs dependencies into `.venv`.
- `scripts/lint` formats and lints with ruff.
- `scripts/develop` runs Home Assistant on port 8123 with the integration
  loaded.

`scripts/develop` uses `config/configuration.yaml`. It has no Bluetooth, so
it can't see a real monitor. Use the tests for most work.

## Tests

```sh
uv run pytest
```

The tests use payloads captured from real monitors. If you have a monitor
that isn't covered, add its payloads to the tests.

## Validation

CI runs hassfest and the HACS checks. To run hassfest locally:

```sh
docker run --rm -v "$PWD":/github/workspace ghcr.io/home-assistant/hassfest
```

The HACS check reads the repository from GitHub, so it only runs in CI.

## Dependencies

Dependencies are pinned in `pyproject.toml` and locked in `uv.lock`.
Renovate opens pull requests to update them.

`pytest-homeassistant-custom-component` pins the Home Assistant version used
in tests. That version, the Bluetooth packages listed with it, and the
`homeassistant` key in `hacs.json` must all match. Renovate leaves them
alone, so update them together by hand.

## License

Contributions are licensed under the [MIT License](LICENSE).
