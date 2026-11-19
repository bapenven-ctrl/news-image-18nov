#!/usr/bin/env python3
"""news-image-20261118 entry program.

Writes the committed front-page image to the harness output path. The
image (entry.png, held in this repository) sums up the world news of
Wednesday 18 November 2026: fifty verified stories on one broadsheet page
- "THE WORLD IN ONE PAGE" - led by the APEC opening in Shenzhen, with the
Gulf war, Manila, the AI markets day, Cyclone Akvan, the Ukraine drone
night, Voyager 1's light-day and the U.S.-Venezuela pact as illustrated
panels, forty-two numbered briefs, a pin-numbered world map and a black
DATE CHECK footer. The image was rendered deterministically with Pillow
from a script in the build session, never AI-generated, so no text is
garbled.

Standard library only. The program simply copies the committed PNG, so
two runs always write byte-identical output.
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "entry.png")


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
    if os.path.getsize(dest) != os.path.getsize(SOURCE):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
