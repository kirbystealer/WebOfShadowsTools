#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#  "python-lzo @ https://github.com/kirbystealer/python-lzo/releases/download/v1.16/python_lzo-1.16-cp38-cp38-win_amd64.whl ; sys_platform == 'win32' and platform_machine == 'AMD64' and python_version == '3.8'",
#  "python-lzo @ https://github.com/kirbystealer/python-lzo/releases/download/v1.16/python_lzo-1.16-cp39-cp39-win_amd64.whl ; sys_platform == 'win32' and platform_machine == 'AMD64' and python_version == '3.9'",
#  "python-lzo @ https://github.com/kirbystealer/python-lzo/releases/download/v1.16/python_lzo-1.16-cp310-cp310-win_amd64.whl ; sys_platform == 'win32' and platform_machine == 'AMD64' and python_version == '3.10'",
#  "python-lzo @ https://github.com/kirbystealer/python-lzo/releases/download/v1.16/python_lzo-1.16-cp311-cp311-win_amd64.whl ; sys_platform == 'win32' and platform_machine == 'AMD64' and python_version == '3.11'",
#  "python-lzo @ https://github.com/kirbystealer/python-lzo/releases/download/v1.16/python_lzo-1.16-cp312-cp312-win_amd64.whl ; sys_platform == 'win32' and platform_machine == 'AMD64' and python_version == '3.12'",
#  "python-lzo @ https://github.com/kirbystealer/python-lzo/releases/download/v1.16/python_lzo-1.16-cp313-cp313-win_amd64.whl ; sys_platform == 'win32' and platform_machine == 'AMD64' and python_version == '3.13'",
# ]
# ///

from wos.cli import main
if __name__ == "__main__":
    main()