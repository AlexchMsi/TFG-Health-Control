import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_module(module_name: str, file_path: Path, package_name: str | None = None):
    if package_name:
        package = types.ModuleType(package_name)
        package.__path__ = [str(file_path.parent)]
        sys.modules[package_name] = package
        full_name = f"{package_name}.{module_name}"
    else:
        full_name = module_name

    sys.modules.pop(full_name, None)
    spec = importlib.util.spec_from_file_location(full_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


def server_collector_path(filename: str) -> Path:
    return ROOT / "agents" / "server-agent" / "src" / "collectors" / filename


def siemens_collector_path(filename: str) -> Path:
    return ROOT / "agents" / "siemens-agent" / "src" / "collectors" / filename


def server_agent_path(filename: str) -> Path:
    return ROOT / "agents" / "server-agent" / "src" / filename


def siemens_agent_path(filename: str) -> Path:
    return ROOT / "agents" / "siemens-agent" / "src" / filename


def recommendation_agent_path(filename: str) -> Path:
    return ROOT / "agents" / "recommendation-agent" / "src" / filename
