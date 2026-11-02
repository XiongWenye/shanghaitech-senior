#!/usr/bin/env python3
"""Deprecated login alias. Plan queries must be requested separately."""
import sys
from senior import main


def run():
    print("该旧入口现在仅执行登录；学分诊断请单独运行 senior.py audit。", file=sys.stderr)
    return main(["login", *sys.argv[1:]])


if __name__ == "__main__":
    run()
