import sys
import logging
from wos.utils import format_hex

def _logger(levels_up=2):
    frame = sys._getframe(levels_up)
    name = frame.f_globals.get("__name__", "__main__")
    return logging.getLogger(name)

def _log(method, msg="", *, print_hex=None):
    log = _logger(3)

    if print_hex is not None:
        if not isinstance(print_hex, (bytes, bytearray, memoryview)):
            raise TypeError("print_hex must be bytes-like")

        hex_str = format_hex(print_hex)
        msg = f"{msg}\n{hex_str}" if msg else hex_str
    else:
        msg = '\t' + msg

    method(msg)

def debug(msg="", *, print_hex=None):
    _log(_logger().debug, msg, print_hex=print_hex)

def info(msg="", *, print_hex=None):
    _log(_logger().info, msg, print_hex=print_hex)

def warning(msg="", *, print_hex=None):
    _log(_logger().warning, msg, print_hex=print_hex)

def error(msg="", *, print_hex=None):
    _log(_logger().error, msg, print_hex=print_hex)

def critical(msg="", *, print_hex=None):
    _log(_logger().critical, msg, print_hex=print_hex)