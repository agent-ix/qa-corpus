//! Static contract between corpus expectations and non-Quire producers.

use std::{collections::BTreeSet, fs, path::Path};

use serde_json::Value;

use crate::corpus::{load_yaml, Case, CorpusError, ErrorCode};

fn invalid(message: impl Into<Box<str>>) -> CorpusError {
    CorpusError::new(ErrorCode::CaseMetadata, message)
}

/// Validate that every external witness kind has one declared producer and
/// that the corpus contains positive and negative examples of the channel.
pub fn validate(root: &Path, cases: &[Case]) -> Result<String, CorpusError> {
    let path = root.join("config/external-channel.json");
    let source = fs::read(&path).map_err(|error| {
        CorpusError::new(ErrorCode::Input, format!("{}: {error}", path.display()))
    })?;
    let manifest: Value = serde_json::from_slice(&source)
        .map_err(|error| invalid(format!("{}: {error}", path.display())))?;
    if manifest["schemaVersion"] != "qa-external-channel-v1" {
        return Err(invalid(
            "external channel schema version is not qa-external-channel-v1",
        ));
    }
    let channels = manifest["channels"]
        .as_object()
        .ok_or_else(|| invalid("external channels must be a mapping"))?;
    for (kind, channel) in channels {
        let tokens = channel["command"]
            .as_array()
            .filter(|tokens| !tokens.is_empty())
            .ok_or_else(|| invalid(format!("{kind}: command is not a nonempty string array")))?;
        if !tokens.iter().all(Value::is_string) || !tokens.iter().any(|token| token == "{repo}") {
            return Err(invalid(format!(
                "{kind}: command must name the controlled repository"
            )));
        }
        if !channel["owner"]
            .as_str()
            .is_some_and(|owner| !owner.is_empty())
        {
            return Err(invalid(format!("{kind}: non-Quire owner is not declared")));
        }
    }
    let mut case_count = 0;
    let mut failures = 0;
    let mut controls = 0;
    let mut observed = BTreeSet::new();
    for case in cases {
        let expect = load_yaml(&root.join(&case.expectation))?;
        let Some(values) = expect.get("external_observations") else {
            continue;
        };
        let values = values.as_array().ok_or_else(|| {
            invalid(format!(
                "{}: external_observations must be a list",
                case.directory.display()
            ))
        })?;
        case_count += 1;
        if values.is_empty() {
            controls += 1;
        } else {
            failures += 1;
        }
        for value in values {
            let kind = value["kind"].as_str().ok_or_else(|| {
                invalid(format!(
                    "{}: external observation has no kind",
                    case.directory.display()
                ))
            })?;
            observed.insert(kind.to_owned());
        }
    }
    if case_count == 0 || failures == 0 || controls == 0 {
        return Err(invalid(format!("external population is incomplete: {case_count} cases, {failures} failures, {controls} controls")));
    }
    for kind in &observed {
        if !channels.contains_key(kind) {
            return Err(invalid(format!(
                "external observations have no producer channel: {kind}"
            )));
        }
    }
    for kind in channels.keys() {
        if !observed.contains(kind) {
            return Err(invalid(format!(
                "external producer channel has no positive observation: {kind}"
            )));
        }
    }
    Ok(format!("external channel: {case_count} cases ({failures} failures, {controls} controls), {} exact producer commands", channels.len()))
}
