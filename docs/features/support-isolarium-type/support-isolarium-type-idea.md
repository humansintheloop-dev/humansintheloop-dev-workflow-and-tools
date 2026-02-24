## Summary

Add an optional `--isolation-type TYPE` argument to `i2code implement` that passes through as `--type TYPE` to the isolarium command.

## Details

- The isolarium CLI accepts `--type TYPE` as a global option (before the subcommand): `isolarium --name <name> --type <type> run ...`
- `i2code implement --isolation-type TYPE` maps directly to this, inserting `--type TYPE` into the isolarium global args
- Passing `--isolation-type` implies `--isolate` — no need to specify both
- This is a pass-through option: isolarium validates the type value, not i2code
- Scope: `i2code implement` only (not `scaffold`)
