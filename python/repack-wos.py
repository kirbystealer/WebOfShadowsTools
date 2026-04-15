#!/usr/bin/env python3

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from wos.repack import main


if __name__ == "__main__":
    main()
