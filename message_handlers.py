"""Per-function handlers for BCP log message results.

Each handler receives a validated result dictionary and returns the data that
should be stored in the database.  Handlers are registered by func_name and
looked up by LogMessageHandler.
"""

from typing import Any, Callable, Dict

Handler = Callable[[Dict[str, Any]], Dict[str, Any]]


def _generic_handler(result: Dict[str, Any]) -> Dict[str, Any]:
    """Default handler: store the raw result as JSON text."""
    return {
        "func_name": result.get("func_name", "unknown"),
        "result": result.get("result"),
        "timestamp": result.get("timestamp"),
    }


def handle_configureslpgbt(result: Dict[str, Any]) -> Dict[str, Any]:
    return _generic_handler(result)


def handle_configureslpgbts(result: Dict[str, Any]) -> Dict[str, Any]:
    return _generic_handler(result)


def handle_resetvfes(result: Dict[str, Any]) -> Dict[str, Any]:
    return _generic_handler(result)


def handle_getbitslips(result: Dict[str, Any]) -> Dict[str, Any]:
    return _generic_handler(result)


def handle_optimizevrefs(result: Dict[str, Any]) -> Dict[str, Any]:
    return _generic_handler(result)


def handle_calibrateadcs(result: Dict[str, Any]) -> Dict[str, Any]:
    return _generic_handler(result)


def handle_optimize_ped_rogue(result: Dict[str, Any]) -> Dict[str, Any]:
    return _generic_handler(result)


def handle_launchprbstest(result: Dict[str, Any]) -> Dict[str, Any]:
    return _generic_handler(result)


HANDLERS: Dict[str, Handler] = {
    "configureslpgbt": handle_configureslpgbt,
    "configureslpgbts": handle_configureslpgbts,
    "resetvfes": handle_resetvfes,
    "getbitslips": handle_getbitslips,
    "optimizevrefs": handle_optimizevrefs,
    "calibrateadcs": handle_calibrateadcs,
    "optimize_ped_rogue": handle_optimize_ped_rogue,
    "launchprbstest": handle_launchprbstest,
}


def get_handler(func_name: str) -> Handler:
    """Return the handler for a func_name, falling back to the generic handler."""
    return HANDLERS.get(func_name, _generic_handler)
