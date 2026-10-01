"""
Cortex plugin hook loader.
Hermes will import this when the plugin is enabled.
"""

from . import CortexPlugin

def get_hook_handler():
    """Return the pre_tool_call handler."""
    plugin = CortexPlugin()
    return plugin.pre_tool_call

def get_description():
    """Plugin description for Hermes."""
    return "Cortex control — action gate, epistemic protocol, experience tracking"
