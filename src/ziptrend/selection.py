"""ZIP-list parsing shared by search and bulk selection controls."""
import re
from .data import normalize_zip


def parse_zip_list(text, available):
    """Return unique available ZIPs and rejected tokens; preserve leading zeros."""
    accepted, rejected = [], []
    available = set(available)
    for token in re.split(r"[\s,;]+", text.strip()):
        if not token:
            continue
        zipcode = normalize_zip(token)
        target, value = (accepted, zipcode) if zipcode in available else (rejected, token)
        if value not in target:
            target.append(value)
    return accepted, rejected
