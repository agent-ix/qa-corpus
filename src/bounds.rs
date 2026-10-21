//! Derived mode and language cells consumed by CI and measurement evidence.

use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
};

use serde_json::{json, Map, Value};

use crate::corpus::{load_yaml, Case, CorpusError, ErrorCode};

fn invalid(message: impl Into<Box<str>>) -> CorpusError {
    CorpusError::new(ErrorCode::CaseMetadata, message)
}

fn required_str<'a>(value: &'a Value, key: &str, context: &str) -> Result<&'a str, CorpusError> {
    value
        .get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| invalid(format!("{context}: `{key}` must be a string")))
}

fn required_array<'a>(
    value: &'a Value,
    key: &str,
    context: &str,
) -> Result<&'a Vec<Value>, CorpusError> {
    value
        .get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| invalid(format!("{context}: `{key}` must be a list")))
}

fn string_set(value: &Value, key: &str, context: &str) -> Result<BTreeSet<String>, CorpusError> {
    let mut result = BTreeSet::new();
    for item in required_array(value, key, context)? {
        let name = item
            .as_str()
            .ok_or_else(|| invalid(format!("{context}: `{key}` contains a non-string")))?;
        if !result.insert(name.to_owned()) {
            return Err(invalid(format!("{context}: `{key}` repeats `{name}`")));
        }
    }
    if result.is_empty() {
        return Err(invalid(format!("{context}: `{key}` is empty")));
    }
    Ok(result)
}

fn module_exists(root: &Path, module: &str) -> bool {
    let base = root.join("modules").join(module);
    if base.join("manifest.yaml").is_file() {
        return true;
    }
    let Ok(entries) = std::fs::read_dir(base) else {
        return false;
    };
    entries
        .flatten()
        .any(|entry| entry.path().join("manifest.yaml").is_file())
}

type CellKey = (String, String, String);

struct Variant<'a> {
    fixture: &'a str,
    module: &'a str,
    ticket: Option<&'a str>,
    subject: Option<&'a str>,
}

/// Derive the public `bounds` and `cases` envelope from validated case metadata.
/// This is the single source used by the CI gate and MP-201/MP-202 evidence.
pub fn derive(root: &Path, cases: &[Case]) -> Result<Value, CorpusError> {
    let declaration = load_yaml(&root.join("corpus.yaml"))?;
    let mut modes = string_set(&declaration, "mode_families", "corpus.yaml")?;
    modes.extend(string_set(&declaration, "reporting_modes", "corpus.yaml")?);
    let states = string_set(&declaration, "bounds_states", "corpus.yaml")?;
    let mut counts: BTreeMap<String, usize> =
        states.iter().map(|state| (state.clone(), 0)).collect();
    let mut covered: BTreeSet<CellKey> = BTreeSet::new();
    let mut pending: BTreeSet<CellKey> = BTreeSet::new();
    let mut variants: BTreeMap<CellKey, Variant<'_>> = BTreeMap::new();
    let mut public_cases = Vec::with_capacity(cases.len());

    for case in cases {
        let value = &case.effective;
        let id = required_str(value, "id", &case.directory.display().to_string())?;
        let mode = required_str(value, "mode", id)?;
        let language = required_str(value, "language", id)?;
        let kind = required_str(value, "kind", id)?;
        let module = required_str(value, "module", id)?;
        if !modes.contains(mode) {
            return Err(invalid(format!("{id}: undeclared mode `{mode}`")));
        }
        let normalized = module
            .trim()
            .trim_matches(|ch| ch == '.' || ch == '/')
            .trim_end_matches('/');
        if normalized.is_empty() || !module_exists(root, normalized) {
            return Err(invalid(format!(
                "{id}: module `{module}` has no manifest under modules/{normalized}/"
            )));
        }
        let relaxation = value
            .get("relaxation_ticket")
            .and_then(Value::as_str)
            .filter(|s| !s.is_empty());
        let subject = value
            .get("declaration_under_test")
            .and_then(Value::as_str)
            .filter(|s| !s.is_empty());
        if normalized == "ecosystem" && (relaxation.is_some() || subject.is_some()) {
            return Err(invalid(format!(
                "{id}: binds the ecosystem module but declares variant metadata"
            )));
        }
        if normalized != "ecosystem" && relaxation.is_some() == subject.is_some() {
            return Err(invalid(format!("{id}: binds variant `{normalized}` and must declare exactly one of `relaxation_ticket` or `declaration_under_test`")));
        }
        let case_name = value.get("case").and_then(Value::as_str).unwrap_or(id);
        let key = (mode.to_owned(), case_name.to_owned(), language.to_owned());
        if kind == "failure" || kind == "regression" {
            if normalized == "ecosystem" {
                covered.insert(key.clone());
            } else {
                variants.insert(
                    key.clone(),
                    Variant {
                        fixture: id,
                        module: normalized,
                        ticket: relaxation,
                        subject,
                    },
                );
            }
        }
        if value.get("pending").is_some_and(|value| !value.is_null()) {
            pending.insert(key);
        }
        let mut public = value.clone();
        public["module"] = Value::String(normalized.to_owned());
        public_cases.push(public);
    }

    let mut matrix = Vec::new();
    let mut declared_cells = 0usize;
    let mut covered_pending = 0usize;
    for row in required_array(&declaration, "inventory", "corpus.yaml")? {
        let mode = required_str(row, "mode", "inventory row")?;
        let case_name = required_str(row, "case", "inventory row")?;
        let source = required_str(row, "source", case_name)?;
        if !modes.contains(mode) {
            return Err(invalid(format!("{case_name}: undeclared mode `{mode}`")));
        }
        let languages = string_set(row, "languages", case_name)?;
        let out_of_scope = row.get("out_of_scope").and_then(Value::as_object);
        if let Some(scoped) = out_of_scope {
            for (language, reason) in scoped {
                if !languages.contains(language) {
                    return Err(invalid(format!("{case_name}: out-of-scope names `{language}`, which the row does not declare applicable")));
                }
                if !reason.as_str().is_some_and(|s| !s.trim().is_empty()) {
                    return Err(invalid(format!(
                        "{case_name}/{language}: out-of-scope with no reason"
                    )));
                }
            }
        }
        let mut cells = Map::new();
        for language in languages {
            declared_cells += 1;
            let key = (mode.to_owned(), case_name.to_owned(), language.clone());
            let mut cell = if let Some(reason) =
                out_of_scope.and_then(|scoped| scoped.get(&language))
            {
                json!({"state":"out-of-scope", "reason": reason})
            } else if covered.contains(&key) {
                json!({"state":"covered"})
            } else if let Some(variant) = variants.get(&key) {
                if let Some(subject) = variant.subject {
                    json!({"state":"out-of-scope", "reason": format!("`{}` tests variant declaration `{}`: {subject}", variant.fixture, variant.module)})
                } else {
                    json!({"state":"GAP", "reason": format!("`{}` ships but binds `{}` rather than the ecosystem declaration, so it exercises no ecosystem mode ({})", variant.fixture, variant.module, variant.ticket.unwrap_or("unknown ticket"))})
                }
            } else {
                json!({"state":"GAP"})
            };
            let state = required_str(&cell, "state", case_name)?;
            let count = counts.get_mut(state).ok_or_else(|| invalid(format!("{case_name}/{language}: graded `{state}`, which corpus.yaml bounds_states does not declare")))?;
            *count += 1;
            if state == "covered" && pending.contains(&key) {
                cell["pending"] = Value::Bool(true);
                covered_pending += 1;
            }
            cells.insert(language, cell);
        }
        matrix.push(json!({"mode":mode,"case":case_name,"source":source,"cells":cells}));
    }
    let graded: usize = counts.values().sum();
    if graded != declared_cells {
        return Err(invalid(format!("the sum invariant does not hold: inventory declares {declared_cells} cells and {graded} were graded")));
    }
    Ok(json!({
        "bounds": {
            "gap_count": counts.get("GAP").copied().unwrap_or(0),
            "covered_count": counts.get("covered").copied().unwrap_or(0),
            "covered_pending_count": covered_pending,
            "out_of_scope_count": counts.get("out-of-scope").copied().unwrap_or(0),
            "declared_cells": declared_cells,
            "matrix": matrix,
        },
        "cases": public_cases,
    }))
}

/// Enforce CI's policy that every applicable cell has a real fixture.
pub fn require_complete(report: &Value) -> Result<(), CorpusError> {
    let mut gaps = Vec::new();
    if let Some(matrix) = report["bounds"]["matrix"].as_array() {
        for row in matrix {
            let Some(cells) = row["cells"].as_object() else {
                continue;
            };
            for (language, cell) in cells {
                if cell["state"] == "GAP" {
                    gaps.push(format!(
                        "{}/{}/{}",
                        row["mode"].as_str().unwrap_or("?"),
                        row["case"].as_str().unwrap_or("?"),
                        language
                    ));
                }
            }
        }
    }
    if gaps.is_empty() {
        Ok(())
    } else {
        Err(invalid(format!(
            "{} applicable mode-language cell(s) have no case: {}",
            gaps.len(),
            gaps.join(", ")
        )))
    }
}

#[cfg(test)]
mod tests {
    use std::path::Path;

    use crate::corpus::discover;

    use super::{derive, require_complete};

    fn root() -> &'static Path {
        Path::new(env!("CARGO_MANIFEST_DIR"))
    }

    /// Trace: FR-065-AC-6, FR-065-AC-19, MP-201, MP-202.
    #[test]
    fn checked_in_corpus_has_a_complete_derived_matrix() {
        let cases = discover(root()).expect("discover checked-in cases");
        let report = derive(root(), &cases).expect("derive checked-in matrix");
        require_complete(&report).expect("all declared cells covered or scoped out");
        let summary = &report["bounds"];
        let declared = summary["declared_cells"].as_u64().expect("declared cells");
        let covered = summary["covered_count"].as_u64().expect("covered cells");
        let scoped = summary["out_of_scope_count"]
            .as_u64()
            .expect("scoped cells");
        assert_eq!(declared, covered + scoped);
        assert_eq!(summary["gap_count"], 0);
        assert_eq!(report["cases"].as_array().map(Vec::len), Some(cases.len()));
    }

    /// Trace: FR-065-AC-44, MP-201. A removed fixture changes the named cell.
    #[test]
    fn removing_one_regression_fixture_creates_a_named_gap() {
        let mut cases = discover(root()).expect("discover checked-in cases");
        let position = cases
            .iter()
            .position(|case| {
                case.effective["kind"] == "regression" && case.effective["module"] == "ecosystem"
            })
            .expect("a regression fixture exists");
        let removed = cases.remove(position);
        let mode = removed.effective["mode"].as_str().expect("mode");
        let name = removed.effective["case"]
            .as_str()
            .or_else(|| removed.effective["id"].as_str())
            .expect("case");
        let language = removed.effective["language"].as_str().expect("language");
        let report = derive(root(), &cases).expect("derive changed matrix");
        assert!(report["bounds"]["gap_count"].as_u64().expect("gap count") > 0);
        let error = require_complete(&report).expect_err("missing fixture must fail CI");
        assert!(error
            .to_string()
            .contains(&format!("{mode}/{name}/{language}")));
    }
}
