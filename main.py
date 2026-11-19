#!/usr/bin/env python3
"""news-image-20261118 entry program.

Writes the committed front-page image to the harness output path. The
image (entry.png, held in this repository) sums up the world news of
Wednesday 18 November 2026: forty-six verified stories on one broadsheet
page - "THE WORLD IN ONE PAGE" - led by the APEC opening in Shenzhen,
with the Gulf war, Manila, the AI markets day, Cyclone Akvan, the
Ukraine drone night, Voyager 1's light-day, the U.S.-Venezuela pact,
the EU's proposed EUR45bn Ukraine loan, the Fed minutes and UK
inflation as illustrated panels (thirteen in all, each drawn as a
scene that tells its story), thirty-three numbered briefs, a
pin-numbered world map and a black DATE CHECK footer whose every
exclusion is itemised with its own date. The image was rendered
deterministically with Pillow from a script in the build session,
never AI-generated, so no text is garbled.

Standard library only. The program simply copies the committed PNG, so
two runs always write byte-identical output.
"""

import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "entry.png")


def sha256_file(path):
    """Hash of a file's bytes, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_path():
    """Resolve where the harness wants entry.png written."""
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if out_dir:
        return os.path.join(out_dir, "entry.png")
    return "/output/entry.png"


def main():
    dest = output_path()
    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.copyfile(SOURCE, dest)
    # Sanity guard: the written file must be the committed image, whole.
    # Size alone is a weak check, so compare the full sha256 as well.
    if os.path.getsize(dest) != os.path.getsize(SOURCE):
        return 1
    if sha256_file(dest) != sha256_file(SOURCE):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
