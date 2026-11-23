from typing import Annotated

import typer
from typer_examples import example

from frappe_manager.output_manager import get_global_output_handler, spinner
from frappe_manager.utils.site import check_docker_images, pull_docker_images


@example(
    "Pull the images fmx's stack runs on",
    "",
)
@example(
    "Say which images have a newer build published, without pulling any",
    "--check",
)
def update_images(
    ctx: typer.Context,
    check: Annotated[bool, typer.Option("--check", help="Report which images have moved in the registry and pull nothing.")] = False,
):
    """Pull the docker images fmx's stack runs on.

    Running containers keep the image they started with until they are recreated.

    Which tags get pulled is fixed by the installed fmx version, so a newer stack starts with fmx self upgrade.

    fmx republishes a release's image tags when their base picks up fixes, and a pull is skipped while the tag is already on disk, so --check is how a host learns it is behind.
    """
    output = get_global_output_handler()
    if check:
        with spinner(output, "Checking published images"):
            behind = check_docker_images()
        # print, not info: the answer IS the command's output, and info is hidden below -v, so
        # `--check` on an up-to-date host printed nothing at all.
        if not behind:
            output.print("Every image matches the build this fmx pins")
            return
        for image, (kind, digest) in behind.items():
            if kind == "pinned":
                output.warning(f"{image.split('@')[0]} pinned to {digest}, not on disk")
            else:
                output.warning(f"{image} has a newer build published ({digest})")
        output.print("Run 'fmx self update-images' to pull them")
        return
    with spinner(output, "Pulling latest Docker images"):
        pull_docker_images()
