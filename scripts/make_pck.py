#!/usr/bin/env python3
"""
Generate a minimal Godot 4 PCK file for the STS2_MCP mod.

A Godot 4 PCK (pack) file bundles resources that the engine loads at runtime.
For a pure C# mod this pack only needs to contain mod_manifest.json so that
the STS2 mod-loader can identify and register the mod.

Usage:
    python make_pck.py <mod_manifest_json> <output_pck>

Example:
    python scripts/make_pck.py mod_manifest.json STS2_MCP.pck
"""

import hashlib
import struct
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Godot 4 PCK binary format (pack format version = 2)
# ---------------------------------------------------------------------------
# Header:
#   magic        : uint32  = 0x43504447  ("GDPC")
#   pack_version : int32   = 2           (Godot 4.x)
#   ver_major    : int32   = 4
#   ver_minor    : int32   = 0
#   ver_patch    : int32   = 0
#   reserved[16] : int32   (64 bytes of zeros)
#   file_count   : int32
#
# File entry (repeated file_count times):
#   path_len : int32      (byte length of path string, including null terminator)
#   path     : char[path_len]   (UTF-8, null-terminated, "res://<name>")
#   offset   : int64      (byte offset of file data from start of PCK)
#   size     : int64      (byte length of file data)
#   md5      : byte[16]   (MD5 hash of file data)
#   flags    : int32      (0 = plain)
#
# File data follows all headers, at the offsets recorded above.
# ---------------------------------------------------------------------------

MAGIC = 0x43504447
PACK_VERSION = 2
VER_MAJOR = 4
VER_MINOR = 0
VER_PATCH = 0


def pack_string(s: str) -> bytes:
    """Encode a string as a length-prefixed, null-terminated byte sequence."""
    encoded = s.encode("utf-8") + b"\x00"
    return struct.pack("<i", len(encoded)) + encoded


def build_pck(files: dict) -> bytes:
    """
    Build a Godot 4 PCK from a dict mapping res:// paths to raw file bytes.
    Returns the complete PCK as a bytes object.
    """
    # Fixed header size:
    #   magic(4) + pack_version(4) + ver_major(4) + ver_minor(4) + ver_patch(4)
    #   + reserved(64) + file_count(4)  = 84 bytes
    header_size = 4 + 4 + 4 + 4 + 4 + 64 + 4

    # Calculate the size of all file-entry descriptors so we know file offsets.
    entry_sizes = []
    for path in files:
        encoded_path = path.encode("utf-8") + b"\x00"
        # path_len(4) + path(n) + offset(8) + size(8) + md5(16) + flags(4)
        entry_sizes.append(4 + len(encoded_path) + 8 + 8 + 16 + 4)

    total_entry_bytes = sum(entry_sizes)

    # File data starts right after header + all entry descriptors.
    data_section_start = header_size + total_entry_bytes

    # Compute each file's absolute offset within the PCK.
    offsets = []
    cursor = data_section_start
    for data in files.values():
        offsets.append(cursor)
        cursor += len(data)

    # ----------------------------------------------------------------
    # Assemble the PCK bytes
    # ----------------------------------------------------------------
    out = bytearray()

    # Header
    out += struct.pack("<I", MAGIC)
    out += struct.pack("<i", PACK_VERSION)
    out += struct.pack("<i", VER_MAJOR)
    out += struct.pack("<i", VER_MINOR)
    out += struct.pack("<i", VER_PATCH)
    out += b"\x00" * 64          # 16 reserved int32 fields
    out += struct.pack("<i", len(files))

    # File entries
    for (path, data), offset in zip(files.items(), offsets):
        encoded_path = path.encode("utf-8") + b"\x00"
        md5 = hashlib.md5(data).digest()
        out += struct.pack("<i", len(encoded_path))
        out += encoded_path
        out += struct.pack("<q", offset)
        out += struct.pack("<q", len(data))
        out += md5
        out += struct.pack("<i", 0)  # flags = 0 (plain)

    # File data
    for data in files.values():
        out += data

    return bytes(out)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <mod_manifest_json> <output_pck>")
        sys.exit(1)

    manifest_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found")
        sys.exit(1)

    manifest_data = manifest_path.read_bytes()

    files = {
        "res://mod_manifest.json": manifest_data,
    }

    pck_bytes = build_pck(files)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pck_bytes)
    print(f"Written {len(pck_bytes)} bytes -> {output_path}")


if __name__ == "__main__":
    main()
