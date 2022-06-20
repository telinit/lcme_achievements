
# Here go some useful utility functions
from typing import Iterable, Any, Dict


def add_to_dict_multival(d: dict[Any, list[Any]], k: Any, v: Any):
    if k in d:
        d[k].append(v)
    else:
        d[k] = [v]


def add_to_dict_multival_set(d: dict[Any, set[Any]], k: Any, v: Any):
    if k in d:
        d[k].add(v)
    else:
        d[k] = {v}


def group_by_type(it: Iterable[Any]) -> dict[type, list[Any]]:
    res: dict[type, list[Any]] = {}
    for x in it:
        add_to_dict_multival(res, type(x), x)
    
    return res