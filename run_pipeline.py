"""
run_pipeline.py
---------------
Orchestrates the full IPTV processing pipeline:
    scan.m3u -> adult_filter -> logos -> order_m3u -> mahdi_iptv.m3u8
"""

import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PIPELINE_STEPS = [
    ("adult_filter", "Removing adult channels"),
    ("logos", "Attaching channel logos"),
    ("order_m3u", "Ordering and numbering channels"),
]


def run() -> None:
    log.info("=" * 60)
    log.info("  IPTV Pipeline  -  Starting")
    log.info("=" * 60)

    t0 = time.time()
    total_steps = len(PIPELINE_STEPS)

    for step_idx, (module_name, description) in enumerate(PIPELINE_STEPS, 1):
        log.info("-" * 60)
        log.info(f"  Step {step_idx}/{total_steps}: {description}")
        log.info("-" * 60)

        try:
            if module_name == "adult_filter":
                import adult_filter
                adult_filter.main()
            elif module_name == "logos":
                import logos
                logos.main()
            elif module_name == "order_m3u":
                import order_m3u
                order_m3u.main()
        except Exception as exc:
            log.error(f"Step '{module_name}' failed: {exc}")
            log.error("Aborting pipeline.")
            sys.exit(1)

    elapsed = time.time() - t0
    log.info("=" * 60)
    log.info(f"  Pipeline complete in {elapsed:.1f}s")
    log.info("=" * 60)


if __name__ == "__main__":
    run()
