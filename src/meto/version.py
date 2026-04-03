from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """Return the installed package version, or 'dev' if not installed."""
    try:
        return version("meto")
    except PackageNotFoundError:
        return "dev"
