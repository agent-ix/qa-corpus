# PRODUCTION code. The shape is taken from
# k8s-orchestration/k8s_orchestration/retry.py:15 — a `#` comment carrying a
# requirement id at column 0, directly above the thing it describes.
#
# `normalize_severity` is a plain function, so `SymbolKind::Function`. CR-061
# made `binds_trace_ids()` false for that kind: production doc comments
# routinely cite the criterion they implement, and binding them would
# mass-manufacture backing out of prose. The tag below is therefore not even a
# binding CANDIDATE — it is missing from the census denominator rather than
# counted as a miss.
#
# The other channel is closed too: `implements` binds only after the literal
# `Implements:` keyword, and this comment does not carry it.
#
# No id is written anywhere in this header on purpose. A tag is the only thing
# in this file that names one.


# TC-001: Warning default.
def normalize_severity(finding):
    return finding.get("severity") or "warning"
