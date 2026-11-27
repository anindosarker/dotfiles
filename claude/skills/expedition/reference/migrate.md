# Migrating a release folder

A release states its format in `status/data/status.json` (`format`); a release with no status file is format `1.0`. `status/report.py <release>` prints one last line when the format is lower than the skill's version. The migrations sit in `scripts/migrate/`, one folder per version step, each with a `README.md` to follow top to bottom:

- [../scripts/migrate/v1.0-v2.0/README.md](../scripts/migrate/v1.0-v2.0/README.md): `format.py`, from flat spec files and tracker statuses to spec folders, task files and the status file. A release in format `1.0` keeps working without it.
- [../scripts/migrate/pre-v1.0/README.md](../scripts/migrate/pre-v1.0/README.md): the seven scripts for folders made before versions were kept. A current script that refuses such a folder names the script to run.

What changed in each version: [../CHANGELOG.md](../CHANGELOG.md).
