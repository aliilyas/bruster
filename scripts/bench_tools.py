"""Shared benchmark configuration and HN provenance, archived with each run."""
import json
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parent.parent / 'benchmarks/competitors.json'
CATALOG = json.loads(CATALOG_PATH.read_text())
CONFIGURATIONS = {tool['id']: tool for tool in CATALOG['tools']}
LINUX_TOOLS = [key for key, tool in CONFIGURATIONS.items() if tool['status'] == 'linux']
LABELS = {key: tool['label'] for key, tool in CONFIGURATIONS.items()}
LEGACY_TOOLS = ['bruster', 'playwright-shell', 'playwright', 'puppeteer', 'agent-browser']


def packages(tools):
    return sorted({package for tool in tools
                   for package in ([CONFIGURATIONS[tool]['package']] if 'package' in CONFIGURATIONS[tool] else [])
                   + CONFIGURATIONS[tool].get('adapter_packages', [])})


def recorded_tools(metadata):
    # Old immutable records predate the registry. Never add new columns to them.
    return metadata.get('tools', LEGACY_TOOLS)


def recorded_labels(record):
    catalog = record['metadata'].get('competitors', {})
    labels = {tool['id']: tool['label'] for tool in catalog.get('tools', [])}
    return {tool: labels.get(tool, LABELS.get(tool, tool))
            for tool in recorded_tools(record['metadata'])}
