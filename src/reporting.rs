//! Grade Quoin's report command against the static reporting cases.

use std::{collections::BTreeSet, fs, path::Path, process::Command};

use serde_json::Value;

use crate::corpus::{controls_by_case, discover, load_yaml, CorpusError, ErrorCode};

fn invalid(message: impl Into<Box<str>>) -> CorpusError {
    CorpusError::new(ErrorCode::Input, message)
}

/// The reporting verdict retains every named mismatch for CI output.
#[derive(Debug)]
pub struct Summary {
    /// Number of authored reporting cases run.
    pub cases: usize,
    /// Errors in report output or its case contract.
    pub failures: Vec<String>,
}

fn ratio_consistency(
    root: &Path,
    case_name: &str,
    expectation: &Value,
    tokens: &[&str],
    failures: &mut Vec<String>,
) -> Result<(), CorpusError> {
    let Some(rule) = expectation.get("ratio_consistent") else {
        return Ok(());
    };
    let Some(decimals) = rule["decimals"]
        .as_i64()
        .filter(|value| (0..=12).contains(value))
    else {
        failures.push(format!(
            "{case_name}: ratio_consistent requires integer `decimals`"
        ));
        return Ok(());
    };
    let Some(repo) = tokens
        .windows(2)
        .find(|pair| pair[0] == "--repo")
        .map(|pair| pair[1])
    else {
        failures.push(format!(
            "{case_name}: ratio_consistent requires a `--repo` input"
        ));
        return Ok(());
    };
    let measurements = root.join(repo).join("spec/evidence/measurements");
    let mut records = fs::read_dir(&measurements)
        .map_err(|error| invalid(format!("{}: {error}", measurements.display())))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| invalid(error.to_string()))?;
    records.sort_by_key(|entry| entry.path());
    let mut checked = 0;
    for record in records {
        let path = record.path();
        if path.extension().is_none_or(|extension| extension != "json") {
            continue;
        }
        let bytes =
            fs::read(&path).map_err(|error| invalid(format!("{}: {error}", path.display())))?;
        let record: Value = serde_json::from_slice(&bytes)
            .map_err(|error| invalid(format!("{}: {error}", path.display())))?;
        for observation in record["observations"].as_array().into_iter().flatten() {
            if observation["state"] != "measured" || observation["shape"] != "ratio" {
                continue;
            }
            let metric = observation["metric"].as_str().unwrap_or("unnamed metric");
            let filename = path
                .file_name()
                .and_then(|name| name.to_str())
                .unwrap_or("record");
            let examined = observation["population"]["examined"].as_f64();
            let matched = observation["population"]["matched"].as_f64();
            let (Some(examined), Some(matched)) = (examined, matched) else {
                failures.push(format!(
                    "{case_name}: {filename} {metric} has no positive examined/matched population"
                ));
                continue;
            };
            if examined <= 0.0 {
                failures.push(format!(
                    "{case_name}: {filename} {metric} has no positive examined/matched population"
                ));
                continue;
            }
            let scale = match observation["unit"].as_str() {
                Some("fraction") => 1.0,
                Some("percent") => 100.0,
                _ => {
                    failures.push(format!(
                        "{case_name}: {filename} {metric} uses unsupported ratio unit {}",
                        observation["unit"]
                    ));
                    continue;
                }
            };
            let factor = 10_f64.powi(decimals as i32);
            let expected = ((matched / examined * scale) * factor).round_ties_even() / factor;
            if observation["value"].as_f64() != Some(expected) {
                failures.push(format!("{case_name}: {filename} {metric} value {} disagrees with {matched}/{examined} = {expected}", observation["value"]));
            }
            checked += 1;
        }
    }
    if checked == 0 {
        failures.push(format!(
            "{case_name}: ratio_consistent checked no ratio observations"
        ));
    }
    Ok(())
}

/// Run each reporting case twice and check exact JSON, refusal, and determinism.
pub fn verify(root: &Path, quoin: &Path) -> Result<Summary, CorpusError> {
    let cases: Vec<_> = discover(root)?
        .into_iter()
        .filter(|case| case.effective["mode"] == "reporting")
        .collect();
    if cases.is_empty() {
        return Err(invalid("verify-reporting: no reporting cases discovered"));
    }
    let declaration = load_yaml(&root.join("corpus.yaml"))?;
    let contract = &declaration["reporting_contract"];
    let mut failures = Vec::new();
    let included: BTreeSet<_> = cases
        .iter()
        .filter(|case| {
            case.effective["kind"] == "failure" || case.effective["kind"] == "regression"
        })
        .filter_map(|case| {
            case.effective["case"]
                .as_str()
                .or_else(|| case.effective["id"].as_str())
        })
        .collect();
    for required in contract["required_cases"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
    {
        if !included.contains(required) {
            failures.push(format!(
                "required reporting cases have no fixture: {required}"
            ));
        }
    }
    let controls = controls_by_case(&cases);
    for refusal in contract["refusal_cases"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
    {
        let Some(subject) = cases.iter().find(|case| case.effective["id"] == refusal) else {
            continue;
        };
        let language = subject.effective["language"].as_str().unwrap_or("");
        let Some(partners) = controls.get(&(refusal.to_owned(), language.to_owned())) else {
            failures.push(format!(
                "{refusal}: refusal case has no comparable-runs control"
            ));
            continue;
        };
        for partner in partners {
            let expected = load_yaml(&root.join(&partner.expectation))?;
            let comparisons = expected["stdout"]["comparisons"].as_array();
            if comparisons.is_none_or(|rows| {
                rows.is_empty()
                    || rows.iter().any(|row| {
                        row["status"] != "comparable"
                            || row["reasons"]
                                .as_array()
                                .is_some_and(|items| !items.is_empty())
                    })
            }) {
                failures.push(format!(
                    "{}: refusal control does not require a reason-free comparable delta",
                    partner.effective["id"].as_str().unwrap_or("unknown")
                ));
            }
        }
    }
    for case in &cases {
        let metadata = &case.effective;
        let name = format!(
            "{} ({})",
            metadata["id"].as_str().unwrap_or("unknown"),
            metadata["issue_ref"].as_str().unwrap_or("no issue")
        );
        let expected = load_yaml(&root.join(&case.expectation))?;
        if let Some(keys) = expected.as_object() {
            let unknown: Vec<_> = keys
                .keys()
                .filter(|key| {
                    ![
                        "exit_code",
                        "stdout",
                        "stderr_contains",
                        "byte_identical",
                        "ratio_consistent",
                    ]
                    .contains(&key.as_str())
                })
                .collect();
            if !unknown.is_empty() {
                failures.push(format!("{name}: unhandled expectation keys {unknown:?}"));
                continue;
            }
        }
        let reproduce = metadata["reproduce"].as_str().unwrap_or("");
        let tokens: Vec<_> = reproduce.split_whitespace().collect();
        if tokens.len() < 2 || tokens[0] != "quoin" || tokens[1] != "report" {
            failures.push(format!("{name}: reproduce must invoke `quoin report`"));
            continue;
        }
        ratio_consistency(root, &name, &expected, &tokens, &mut failures)?;
        let run = || {
            Command::new(quoin)
                .args(&tokens[1..])
                .current_dir(root)
                .output()
        };
        let first =
            run().map_err(|error| invalid(format!("{name}: report invocation failed: {error}")))?;
        let second = run().map_err(|error| {
            invalid(format!(
                "{name}: repeated report invocation failed: {error}"
            ))
        })?;
        let wanted_exit = expected["exit_code"].as_i64().unwrap_or(0);
        if i64::from(first.status.code().unwrap_or(-1)) != wanted_exit {
            failures.push(format!(
                "{name}: exit expected {wanted_exit}, got {}: {}",
                first.status.code().unwrap_or(-1),
                String::from_utf8_lossy(&first.stderr).trim()
            ));
        }
        if expected["byte_identical"] == true
            && (first.stdout != second.stdout || first.stderr != second.stderr)
        {
            failures.push(format!("{name}: repeated render was not byte-identical"));
        }
        if let Some(wanted) = expected.get("stdout") {
            match serde_json::from_slice::<Value>(&first.stdout) {
                Ok(actual) if &actual != wanted => failures.push(format!(
                    "{name}: JSON differs: expected {wanted}, got {actual}"
                )),
                Err(error) => failures.push(format!("{name}: stdout is not JSON: {error}")),
                _ => {}
            }
        }
        let stderr = String::from_utf8_lossy(&first.stderr);
        for fragment in expected["stderr_contains"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
        {
            if !stderr.contains(fragment) {
                failures.push(format!("{name}: stderr lacks {fragment:?}"));
            }
        }
    }
    Ok(Summary {
        cases: cases.len(),
        failures,
    })
}

#[cfg(test)]
mod tests {
    use std::fs;

    use serde_json::json;

    use super::ratio_consistency;

    /// Trace: the reporting corpus's opted-in ratio contract is derived from counts.
    #[test]
    fn ratio_consistency_rejects_a_rendered_value_unbacked_by_counts() {
        let root = tempfile::tempdir().unwrap();
        let records = root.path().join("input/spec/evidence/measurements");
        fs::create_dir_all(&records).unwrap();
        fs::write(
            records.join("run.json"),
            json!({"observations":[
                {"state":"measured", "shape":"ratio", "metric":"recall", "unit":"percent",
                 "population":{"examined":4,"matched":1}, "value":30.0}
            ]})
            .to_string(),
        )
        .unwrap();
        let mut failures = Vec::new();
        ratio_consistency(
            root.path(),
            "case",
            &json!({"ratio_consistent":{"decimals":1}}),
            &["quoin", "report", "--repo", "input"],
            &mut failures,
        )
        .unwrap();
        assert_eq!(failures.len(), 1);
        assert!(failures[0].contains("30.0 disagrees with 1/4 = 25"));
        fs::write(
            records.join("run.json"),
            json!({"observations":[
                {"state":"measured", "shape":"ratio", "metric":"recall", "unit":"percent",
                 "population":{"examined":4,"matched":1}, "value":25.0}
            ]})
            .to_string(),
        )
        .unwrap();
        failures.clear();
        ratio_consistency(
            root.path(),
            "case",
            &json!({"ratio_consistent":{"decimals":1}}),
            &["quoin", "report", "--repo", "input"],
            &mut failures,
        )
        .unwrap();
        assert!(failures.is_empty());
    }
}
