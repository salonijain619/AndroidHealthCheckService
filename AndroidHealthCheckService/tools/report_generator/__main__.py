"""Allow ``python -m tools.report_generator`` to invoke the CLI."""
from tools.report_generator.cli import main

if __name__ == "__main__":
    import sys

    sys.exit(main())
