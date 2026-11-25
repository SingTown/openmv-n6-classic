#!/usr/bin/env python3
# This file is part of the OpenMV project.
#
# This work is licensed under the MIT license, see the file LICENSE for details.
#
# Exports the ST Edge AI conversion settings a board's ROMFS models were built
# with, in the form OpenMV IDE reads from a board's firmware folder:
#
#   neuralart.json   a single "default" profile that points at stm32n6.mpool
#   stm32n6.mpool    the memory pool file of the board's profile
#
# The IDE converts models a user adds to the ROMFS with these two files, so a
# board whose models need a different memory pool (for example one without
# external RAM) must ship its own copies, or user models are converted for
# memory the board does not have.

import argparse
import json
import os
import shutil
import sys

SCRIPTS_DIR = os.path.join("lib", "stai", "scripts")


def board_profile(romfs_config):
    """Returns the single conversion profile used by the board's ROMFS models."""
    profiles = set()
    for partition in romfs_config.values():
        for entry in partition.get("entries", []):
            if "profile" in entry:
                profiles.add(entry["profile"])
    if len(profiles) != 1:
        raise ValueError(
            "expected the ROMFS models to use exactly one profile, found: "
            + (", ".join(sorted(profiles)) or "none")
            + " (pass --profile to choose one)"
        )
    return profiles.pop()


def ide_options(options):
    """The IDE appends its own optimization level where the template has a '%'."""
    tokens = options.split()
    out = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token == "--optimization":
            skip = True
            continue
        out.append(token)
    return " ".join(out + ["%"])


def main():
    parser = argparse.ArgumentParser(description="Export ST Edge AI settings for OpenMV IDE.")
    parser.add_argument("--top-dir", required=True, help="Top directory")
    parser.add_argument("--config", required=True, help="Board romfs json config file.")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--profile", default=None, help="Profile to export. Default: the one the config uses.")
    args = parser.parse_args()

    scripts_dir = os.path.join(args.top_dir, SCRIPTS_DIR)
    with open(os.path.join(scripts_dir, "neuralart.json")) as f:
        neuralart = json.load(f)
    with open(args.config) as f:
        romfs_config = json.load(f)

    try:
        name = args.profile or board_profile(romfs_config)
        profile = neuralart["Profiles"][name]
    except (ValueError, KeyError) as e:
        print(f"Error: cannot select a conversion profile for {args.config}: {e}", file=sys.stderr)
        sys.exit(1)

    exported = {
        "Globals": neuralart.get("Globals", {}),
        "Profiles": {
            "default": {
                "memory_pool": "stm32n6.mpool",
                "options": ide_options(profile["options"]),
            }
        },
    }
    with open(os.path.join(args.out_dir, "neuralart.json"), "w") as f:
        json.dump(exported, f, indent=4)
        f.write("\n")
    shutil.copyfile(
        os.path.join(scripts_dir, profile["memory_pool"]),
        os.path.join(args.out_dir, "stm32n6.mpool"),
    )


if __name__ == "__main__":
    main()
