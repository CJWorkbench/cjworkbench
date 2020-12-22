from typing import Any, Iterable, List, Tuple


def find_deletable_ids(
    *, ids_and_sizes: Iterable[Tuple[Any, int]], n_limit: int, size_limit: int
) -> List[Any]:
    """Given a sequence of object IDs and their sizes, choose some to delete.

    Rules (higher rule trumps lower rules):

        * Never return the first object's ID. It's "sacred".
        * Accumulate `size`; return all IDs once it exceeds `size_limit`.
        * Accumulate `n` (number of IDs); return all IDs past `n_limit`.
    """

    # walk over files from newest to oldest, deleting once we're too far.
    sum_size = 0
    ret = []

    for i, (id, size) in enumerate(ids_and_sizes):
        sum_size += size
        if i > 0:
            if (
                i >= n_limit  # too many files -- costs in # of operations
                or sum_size > size_limit  # too many GB -- costs in GB/mo
            ):
                ret.append(id)

    return ret
