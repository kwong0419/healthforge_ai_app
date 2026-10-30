from pathlib import Path

import streamlit.components.v1 as components

# Remembers data in the visitor's own browser (localStorage), so nothing is stored on
# the server. Each call renders an invisible component, which runs once per new request.
_component = components.declare_component(
    "browser_storage", path=str(Path(__file__).parent / "browser_storage_frontend")
)


def read_item(name: str, key: str) -> str | None:
    """
    The stored text ("" if there is none), or None until the browser has answered,
    which takes one rerun after the first call.
    """
    return _component(action="get", name=name, key=key, default=None)


def write_item(name: str, value: str, key: str) -> None:
    """Stores value. Use a key that changes with the value, so each new value is written."""
    _component(action="set", name=name, value=value, key=key, default=None)


def remove_item(name: str, key: str) -> None:
    _component(action="remove", name=name, key=key, default=None)
