# Mixed status columns — issue409

This authored declaration reproduces the real process61a20e0 conflict: one global
Status selector cannot describe a second table whose owning schema says Coverage
Status. It intentionally has no override before the field exists. The repair
requires BOTH the additive engine selector AND the explicit declaration;
a missing selected column must never trigger fallback or guessing.

Source locus: agent-ix/quire-rs#409, agent-ix/quoin#350, process FR003/manifest
functional_coverage columns versus traceability.status.column. No copied corpus
expectation is changed to excuse a detector. All source-language controls differ
only in their table header; their two test declarations are identical.

This is a configuration expressiveness defect, not a false detector finding.
The existing missing-selected-column diagnostic remains correct for these exact
inputs after #409. Therefore these cases bank the live diagnostic permanently,
without a pending claim that would incorrectly require it to disappear on an
unchanged declaration. A separate explicit-override variant and language-matched
cases will exercise the new feature after implementation. The original failure
and controls remain unchanged as no-guessing and default-compatibility controls.
The corpus pending behaviour-change mechanism requires an exact count or row
change; this feature changes neither, and no synthetic count is claimed.
