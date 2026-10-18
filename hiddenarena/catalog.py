"""Which harnesses and providers hiddenarena can run, and how one harness is pointed at one model.

A harness-interface harness speaks one API shape (anthropic or openai) to the provider it names. To run
it on another vendor's model, keep the shape and swap the provider for that vendor's endpoint of the same
shape. A harness that can't be pointed at the model (no endpoint, no key) is unavailable, not broken.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import hi_cli
from harness_interface import Harness, Provider

HARNESSES = Path(hi_cli.__file__).parent / "harnesses"
ENDPOINTS = {                                        # vendor -> API shape -> base url
    "anthropic": {"anthropic": "https://api.anthropic.com"},
    "openai": {"openai": "https://api.openai.com/v1"},
    "deepseek": {"anthropic": "https://api.deepseek.com/anthropic", "openai": "https://api.deepseek.com/v1"},
    "google": {"openai": "https://generativelanguage.googleapis.com/v1beta/openai"},
}
KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "deepseek": "DEEPSEEK_API_KEY",
        "google": "GEMINI_API_KEY"}
SHIPPED = {                                          # a shipped harness's provider name -> (vendor, shape)
    "anthropic": ("anthropic", "anthropic"), "openai": ("openai", "openai"),
    "deepseek": ("deepseek", "anthropic"), "deepseek-openai": ("deepseek", "openai"),
}


class Unavailable(Exception):
    """A harness can't be pointed at the provider or model asked for."""


@dataclass(frozen=True)
class Target:
    """One harness, ready to run: its folder, the provider it now calls, and the model it is asked for."""
    name: str
    folder: Path
    harness: Harness
    provider: Provider
    model: str                                       # "" means the harness's own default


def endpoint(vendor: str, shape: str, env: Mapping[str, str]) -> tuple[str, str]:
    """(url, key) of a vendor's endpoint for an API shape."""
    if shape not in ENDPOINTS.get(vendor, {}):
        raise Unavailable(f"{vendor} has no {shape}-shaped endpoint")
    if not env.get(KEYS[vendor]):
        raise Unavailable(f"{KEYS[vendor]} is not set")
    return ENDPOINTS[vendor][shape], env[KEYS[vendor]]


class Catalog:
    def __init__(self, folder: Path = HARNESSES, env: Mapping[str, str] = os.environ):
        self.folder, self.env = folder, env

    def names(self) -> list[str]:
        return sorted(p.name for p in self.folder.iterdir() if (p / "harness.json").is_file())

    def target(self, name: str, model: str = "") -> Target:
        """The harness on `vendor/model`, or on its own default provider and model when none is named."""
        folder = self.folder / name
        harness = Harness.from_folder(folder)
        if harness.provider not in SHIPPED:
            raise Unavailable(f"unknown provider {harness.provider!r}")
        vendor, shape = SHIPPED[harness.provider]
        if model:
            vendor, _, model = model.partition("/")
            if vendor not in ENDPOINTS or not model:
                raise Unavailable(f"{vendor!r} is not a known provider, or no model is named")
        url, key = endpoint(vendor, shape, self.env)
        return Target(name, folder, harness, Provider(vendor, url, key), model)
