I want to

rename `i2code manage-tracking` to `i2code tracking setup`

The `setup` subcommand always performs migration (no `--migrate` flag needed). The `--link DIR` and `--dry-run` flags are preserved as optional.

The outcome of executing this command is:

* `.hitl/{sessions, issues}` directories will be created
* `.gitignore` will be updated to ignore `.hitl/{sessions, issues}` and ignores of `.claude/{sessions, issues}` files removed
* All `.claude/{sessions, issues}` files (legacy format) will be migrated to `.hitl/{sessions, issues}` (new format)
* Legacy format files in subdirectories will be migrated to new format relative symbolic links to the top-level directory `.hitl/{sessions, issues}` files
* New format files in subdirectories will be migrated to new format relative symbolic links to the top-level directory `.hitl/{sessions, issues}` files
* If an optional `--link link-dir` is specified then:
  * If the top-level `.hitl/{sessions, issues}` are already links to subdirs of link-dir nothing is done
  * If the top-level `.hitl/{sessions, issues}` are directories their contents are moved to subdirs of link-dir and the top-level `.hitl/{sessions, issues}` are replaced with links to those subdirs
  * If the top-level `.hitl/{sessions, issues}` are links to a different directory an error is raised and no changes are made

Additional properties:

* The command is fully idempotent — safe to run repeatedly with informational output
* The old `manage-tracking` command is removed entirely (no deprecated alias)
* `tracking` is a Click command group for cleaner namespace (no other subcommands planned)
