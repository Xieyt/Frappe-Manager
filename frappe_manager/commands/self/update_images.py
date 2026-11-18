import typer
from typer_examples import example

from frappe_manager.output_manager import get_global_output_handler, spinner
from frappe_manager.utils.site import check_docker_images, pull_docker_images


@example(
    "Pull the images fm's stack runs on",
    "",
)
@example(
    "Say which images have a newer build published, without pulling any",
    "--check",
)
def update_images(
    ctx: typer.Context,
    check: bool = typer.Option(False, "--check", help="Report which images have moved in the registry and pull nothing."),
):
    """Pull the docker images fm's stack runs on.

    Running containers keep the image they started with until they are recreated.

    Which tags get pulled is fixed by the installed fm version, so a newer stack starts with fm self upgrade.

    fm republishes a release's image tags when their base picks up fixes, and a pull is skipped while the tag is already on disk, so --check is how a host learns it is behind.
    """
    output = get_global_output_handler()
    if check:
        with spinner(output, "Checking published images"):
            behind = check_docker_images()
        if not behind:
            output.info("Every image is the build the registry publishes.")
            return
        for image, published in behind.items():
            output.warning(f"{image} has a newer build published ({published})")
        output.info("Run 'fm self update-images' to pull them.")
        return
    with spinner(output, "Pulling latest Docker images"):
        pull_docker_images()
