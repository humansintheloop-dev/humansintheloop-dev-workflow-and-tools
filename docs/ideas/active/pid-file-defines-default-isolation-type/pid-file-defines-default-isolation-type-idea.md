# pid.yaml defines default isolation type


## pid.yaml

A project can have a `pid.yaml` file that defines the default isolation type for the project. 
This file is located in the project repo root and is optional.

```yaml
isolarium:
    isolation_type: "nono|container|vm"

```

The `isolarium` and `isolation_type` keys are optional.

## `i2code implement`

When the `pid.yaml` file is present and contains `isolarium.isolation_type` key, 

* the `i2code implement` command will use the isolation type defined in the file as the default isolation type for the project.
* User can specify `--isolation-type type` to override the default isolation type defined in the `pid.yaml` file.
* User can specify `--isolation-type none` to override the default isolation type defined in the `pid.yaml` file and specify that no isolation type should be used.

If the `pid.yaml` file is not present or does not contain `isolarium.isolation_type` key, the `i2code implement` command behave as it currently does.

## `i2code go` configure implement options

When the `pid.yaml` file is present and contains `isolarium.isolation_type` key, then it defines the default option that `i2code go` presents when prompting for the isolation type

In addition, if the user selects `none` then that value is saved as configuration option.

If the `pid.yaml` file is not present or does not contain `isolarium.isolation_type` key, then `i2code go` will prompt for configuration options as it currently does.



