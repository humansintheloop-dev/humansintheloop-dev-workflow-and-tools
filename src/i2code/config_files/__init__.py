from importlib.resources import files


def default_config_dir() -> str:
    return str(files("i2code.config_files"))
