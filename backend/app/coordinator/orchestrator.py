from __future__ import annotations

from app.agents import edit, gen_image, gen_video, indexer, prompting, qa_safety, qa_style
from app.core import cost
from app.core.logging import log


def run_cycle(n: int) -> list[dict]:
    """Runs a full generation cycle: propose → generate → QA → index.

    Orchestrates agents sequentially per variation, logs failures, continues batch.

    Args:
        n: Number of variations to generate

    Returns:
        List of metadata dicts for successfully indexed videos

    Raises:
        RuntimeError: If budget exceeded or critical failure
    """
    log.info(f"cycle_start n={n}")
    cost.reset_cycle()

    # Propose variations
    try:
        proposals = prompting.propose(n)
        log.info(f"proposed_variations count={len(proposals)}")
    except Exception as e:
        log.error(f"prompting_fail: {type(e).__name__}: {e}", exc_info=True)
        raise

    results = []

    # Process each variation sequentially
    for p in proposals:
        vid_id = p["id"]
        log.info(f"variation_start id={vid_id}")

        try:
            # Generate image
            img = gen_image.generate(p)
            log.info(f"image_generated id={vid_id} path={img}")

            # Generate video
            vid = gen_video.from_image(img, p)
            log.info(f"video_generated id={vid_id} path={vid}")

            # Edit (music, effects; NO text/captions/voice)
            cut = edit.polish(vid, p)
            log.info(f"video_edited id={vid_id} path={cut}")

            # QA gates
            qa_style.ensure(cut, p)
            log.info(f"qa_style_pass id={vid_id}")

            qa_safety.ensure(cut, p)
            log.info(f"qa_safety_pass id={vid_id}")

            # Index to videos.json
            meta = indexer.index(cut, p)
            log.info(f"indexed id={vid_id}")

            results.append(meta)

        except Exception as e:
            log.error(
                f"variation_fail id={vid_id} reason={type(e).__name__}:{e}",
                exc_info=True,
            )
            # Continue with next variation

    log.info(f"cycle_complete success={len(results)} fail={n - len(results)}")
    return results
