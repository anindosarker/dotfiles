# Migrating a release folder

A release states its format in `status/data/status.json` (`format`); a release with no status file is format `1.0`. `status/report.py <release>` prints one last line when the format is lower than the skill's version. The migrations sit in `scripts/migrate/`, one folder per version step, each with a `README.md` to follow top to bottom:

- [../scripts/migrate/v2.1-v2.2/README.md](../scripts/migrate/v2.1-v2.2/README.md): `format.py`, to the status words of format 2.2 for the queue items, decisions, epics, specs, milestones and tasks, one decision file per decision in `decisions/` with `decisions.md` as their list, the epic file without its `decisions:` and `specs:` lines, and no `status/sprints.md`. A release in format `2.1` keeps working without it; a release of format 2.2 that still has the decisions board gets the decision files alone from the same command.
- [../scripts/migrate/v2.0-v2.1/README.md](../scripts/migrate/v2.0-v2.1/README.md): `format.py`, from the kanban board `queue.md` to one item file per card in `queue/` and `queue.md` as a list. A release in format `2.0` keeps working without it.
- [../scripts/migrate/v1.0-v2.0/README.md](../scripts/migrate/v1.0-v2.0/README.md): `format.py`, from flat spec files and tracker statuses to spec folders, task files and the status file. A release in format `1.0` keeps working without it.
- [../scripts/migrate/pre-v1.0/README.md](../scripts/migrate/pre-v1.0/README.md): the seven scripts for folders made before versions were kept. A current script that refuses such a folder names the script to run.

What changed in each version: [../CHANGELOG.md](../CHANGELOG.md).
