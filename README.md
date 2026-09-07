# Home Assistant Otodata Bluetooth Low Energy

A Home Assistant integration for picking up Bluetooth Low Energy (BLE) messages from an
Otodata fuel tank monitor.

---

## What?

This repository contains multiple files, here is a overview:

File | Purpose | Documentation
-- | -- | --
`.devcontainer.json` | Used for development/testing with Visual Studio Code. | [Documentation](https://code.visualstudio.com/docs/remote/containers)
`.github/renovate.json` | Dependency update configuration for Renovate (enabled by default). | [Documentation](https://docs.renovatebot.com/configuration-options/)
`.github/_dependabot.yml` | Dependency update configuration for Dependabot (disabled, see "Dependency updates" below). | [Documentation](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)
`.github/ISSUE_TEMPLATE/*.yml` | Templates for the issue tracker | [Documentation](https://help.github.com/en/github/building-a-strong-community/configuring-issue-templates-for-your-repository)
`custom_components/integration_blueprint/*` | Integration files, this is where everything happens. | [Documentation](https://developers.home-assistant.io/docs/creating_component_index)
`CONTRIBUTING.md` | Guidelines on how to contribute. | [Documentation](https://help.github.com/en/github/building-a-strong-community/setting-guidelines-for-repository-contributors)
`LICENSE` | The license file for the project. | [Documentation](https://help.github.com/en/github/creating-cloning-and-archiving-repositories/licensing-a-repository)
`README.md` | The file you are reading now, should contain info about the integration, installation and configuration instructions. | [Documentation](https://help.github.com/en/github/writing-on-github/basic-writing-and-formatting-syntax)
`requirements_dev.txt` | Python packages used for development/testing this integration (also installs lint tooling via `requirements_lint.txt`). | [Documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files)
`requirements_lint.txt` | Python packages used to lint this integration (installed by the Lint CI job). | [Documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files)
`requirements_common.txt` | Python packages common to CI and local dev, installed first so any pip upgrade completes before other dependencies (e.g. a modern pip). | [Documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files)

## Dependency updates

This template ships with configuration for **two** dependency update tools. Pick
**one** and remove or disable the other:

- **Renovate** (`.github/renovate.json`) is enabled by default.
- **Dependabot** (`.github/_dependabot.yml`) is included but disabled — the `_`
  prefix means GitHub ignores it. To use Dependabot instead, rename the file
  back to `.github/dependabot.yml` and delete `.github/renovate.json`.

## How?

1. Create a new repository in GitHub, using this repository as a template by clicking the "Use this template" button in the GitHub UI.
1. Open your new repository in Visual Studio Code devcontainer (Preferably with the "`Dev Containers: Clone Repository in Named Container Volume...`" option).
1. Rename all instances of the `integration_blueprint` to `custom_components/<your_integration_domain>` (e.g. `custom_components/awesome_integration`).
1. Rename all instances of the `Integration Blueprint` to `<Your Integration Name>` (e.g. `Awesome Integration`).
1. Run the `scripts/develop` to start HA and test out your new integration.

## Next steps

These are some next steps you may want to look into:
- Add tests to your integration, [`pytest-homeassistant-custom-component`](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component) can help you get started.
- Add brand images (logo/icon).
- Create your first release.
- Share your integration on the [Home Assistant Forum](https://community.home-assistant.io/).
- Submit your integration to [HACS](https://hacs.xyz/docs/publish/start).
