import pkgutil
from pathlib import Path

_FIXTURES_ROOT = Path(__file__).parent / "fixtures"

pytest_plugins = [
    mod.name for mod in pkgutil.walk_packages([_FIXTURES_ROOT.as_posix()], prefix="tests.fixtures.") if not mod.ispkg
]
