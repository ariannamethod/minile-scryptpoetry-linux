"""Entry point for running the Arianna Method server via ``python -m arianna_core``."""

import os
import sys

from .server import serve


def main() -> None:
    """Launch the web server on the specified port.

    The port can be specified as the first command line argument or via the
    ``PORT`` environment variable. If neither is provided it defaults to
    ``8000``. This mirrors typical PaaS conventions like Railway's.
    """

    port_str = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PORT", "8000")
    port = int(port_str)
    serve(port)


if __name__ == "__main__":
    main()
