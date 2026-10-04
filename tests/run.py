#!/usr/bin/env python3
"""Run the tests with pytest when it is installed, else with this small runner.

    python3 tests/run.py            # every test file
    python3 tests/run.py calendar   # files whose name contains 'calendar'

The runner supports the one fixture the tests use, tmp_path.
"""
import importlib.util
import inspect
import os
import pathlib
import shutil
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def main(argv):
    try:
        import pytest  # noqa: F401
        args = [HERE, "-q"] + (["-k", argv[0]] if argv else [])
        return pytest.main(args)
    except ImportError:
        pass
    files = sorted(f for f in os.listdir(HERE) if f.startswith("test_") and f.endswith(".py"))
    if argv:
        files = [f for f in files if argv[0] in f]
    passed, failed = 0, []
    for f in files:
        spec = importlib.util.spec_from_file_location(f[:-3], os.path.join(HERE, f))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if not name.startswith("test_") or fn.__module__ != mod.__name__:
                continue
            kwargs, tmp = {}, None
            if "tmp_path" in inspect.signature(fn).parameters:
                tmp = tempfile.mkdtemp(prefix="cursitor-test-")
                kwargs["tmp_path"] = pathlib.Path(tmp)
            try:
                fn(**kwargs)
                passed += 1
            except Exception as exc:
                if type(exc).__name__ == "Skipped":
                    passed += 1
                    continue
                failed.append((f, name, traceback.format_exc()))
            finally:
                if tmp:
                    shutil.rmtree(tmp, ignore_errors=True)
    for f, name, tb in failed:
        print("FAIL %s::%s\n%s" % (f, name, tb))
    print("%d passed, %d failed" % (passed, len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
