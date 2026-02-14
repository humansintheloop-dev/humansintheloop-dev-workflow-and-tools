"""Thread-level pure functions."""

from i2code.plan._helpers import _extract_thread_sections, append_change_history
from i2code.plan.plans import fix_numbering


def reorder_threads(plan: str, thread_order: list[int], rationale: str) -> str:
    """Reorder threads according to the specified ordering and renumber.

    Raises ValueError if thread_order doesn't contain exactly the set of
    existing thread numbers.
    """
    preamble, threads, postamble = _extract_thread_sections(plan)

    existing_numbers = {num for num, _ in threads}
    order_set = set(thread_order)

    if len(thread_order) != len(set(thread_order)):
        raise ValueError("reorder-threads: --order contains duplicate thread numbers")

    if order_set != existing_numbers:
        missing = existing_numbers - order_set
        extra = order_set - existing_numbers
        parts = []
        if missing:
            parts.append(f"missing threads: {sorted(missing)}")
        if extra:
            parts.append(f"nonexistent threads: {sorted(extra)}")
        raise ValueError(f"reorder-threads: --order does not match existing threads ({', '.join(parts)})")

    # Build lookup by thread number
    thread_by_num = {num: text for num, text in threads}

    # Reassemble in new order
    reordered = [thread_by_num[n] for n in thread_order]
    assembled = preamble + '\n'.join(reordered) + postamble

    result = fix_numbering(assembled)
    return append_change_history(result, "reorder-threads", rationale)
