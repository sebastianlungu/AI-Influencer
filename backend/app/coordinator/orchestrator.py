from __future__ import annotations

from app.agents import (
    gen_image,
    image_indexer,
    prompting,
)
from app.core import cost
from app.core.logging import log


def generate_images_cycle(n: int) -> list[dict]:
    """Runs image generation cycle only: propose → generate → index to images.json.

    This is the new rating workflow: images are generated and indexed for review.
    User then rates images (dislike/like/superlike) before video generation.

    Args:
        n: Number of image variations to generate

    Returns:
        List of metadata dicts for successfully indexed images

    Raises:
        RuntimeError: If budget exceeded or critical failure
    """
    log.info(f"image_cycle_start n={n}")
    cost.reset_cycle()

    # Propose variations
    try:
        proposals = prompting.propose(n)
        log.info(f"proposed_variations count={len(proposals)}")
    except Exception as e:
        log.error(f"prompting_fail: {type(e).__name__}: {e}", exc_info=True)
        raise

    results = []

    # Process each variation: generate image only
    for p in proposals:
        img_id = p["id"]
        log.info(f"image_start id={img_id}")

        try:
            # Generate image
            img_path = gen_image.generate(p)
            log.info(f"image_generated id={img_id} path={img_path}")

            # Index to images.json for review
            meta = image_indexer.index(img_path, p)
            log.info(f"image_indexed id={img_id} status=pending_review")

            results.append(meta)

        except Exception as e:
            log.error(
                f"image_fail id={img_id} reason={type(e).__name__}:{e}",
                exc_info=True,
            )
            # Continue with next variation

    log.info(f"image_cycle_complete success={len(results)} fail={n - len(results)}")
    return results


