"""Verifies the native `libvalkey` response parser is actually installed.

valkey-py auto-detects and switches to libvalkey when it's importable —
there's no separate flag to flip. So the correct diagnostic for "is the
native parser active" is: is `libvalkey` importable and does it expose
the `Reader` class valkey-py's parser layer relies on. This runs as a
pure unit test; it needs no running Valkey server.
"""


def test_libvalkey_native_parser_is_installed() -> None:
    import libvalkey

    assert hasattr(libvalkey, "Reader"), (
        "libvalkey is importable but missing the Reader class valkey-py expects; "
        "the 'valkey[libvalkey]' extra may not have built correctly for this platform"
    )
