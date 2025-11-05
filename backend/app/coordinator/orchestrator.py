from __future__ import annotations

from app.agents import (
    image_indexer,
    prompting,
)
from app.core import cost, shot_processor
from app.core.logging import log
from app.clients.provider_selector import image_client


def generate_images_cycle(n: int) -> list[dict]:
    """Runs shot generation cycle: propose → generate master → dual export → index.

    Mobile-first workflow:
    - One Leonardo generation @ 1440×2560 (9:16 master)
    - Auto-export two variants: 1080×1920 (video) + 1080×1350 (feed)
    - Indexed for review with dual aspect ratios

    Args:
        n: Number of shot variations to generate

    Returns:
        List of metadata dicts for successfully indexed shots

    Raises:
        RuntimeError: If budget exceeded or critical failure
    """
    log.info(f"shot_cycle_start n={n}")
    cost.reset_cycle()

    # Propose variations with 4:5 safe-area constraints
    try:
        proposals = prompting.propose(n)
        log.info(f"proposed_variations count={len(proposals)}")
    except Exception as e:
        log.error(f"prompting_fail: {type(e).__name__}: {e}", exc_info=True)
        raise

    results = []

    # Process each variation: generate shot with dual exports
    for p in proposals:
        shot_id = p["id"]
        log.info(f"shot_start id={shot_id}")

        try:
            # Generate shot: one Leonardo call → three derivatives (master + video + feed)
            shot_meta = shot_processor.generate_shot(p, image_client)
            log.info(
                f"shot_generated id={shot_id}, exports: "
                f"video={shot_meta.video_9x16_path}, feed={shot_meta.feed_4x5_path}"
            )

            # Index to images.json for review
            meta = image_indexer.index(shot_meta, p)
            log.info(
                f"shot_indexed id={shot_id} status=pending_review, "
                f"comp_warning={shot_meta.composition_warning}"
            )

            results.append(meta)

        except Exception as e:
            log.error(
                f"shot_fail id={shot_id} reason={type(e).__name__}:{e}",
                exc_info=True,
            )
            # Continue with next variation

    log.info(f"shot_cycle_complete success={len(results)} fail={n - len(results)}")
    return results


