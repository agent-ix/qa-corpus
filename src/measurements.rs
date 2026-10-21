//! Governed MP-201 and MP-202 collection derived from corpus data and runner baselines.

use std::{collections::BTreeSet, fs, path::Path, process::Command};

use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use time::OffsetDateTime;

use crate::{
    bounds,
    corpus::{discover, CorpusError, ErrorCode},
};

const RUNNERS: [&str; 2] = ["quire-rs", "quoin"];
const CONFIG_FILES: [&str; 3] = [
    "config/metrics.json",
    "assurance/MP-201-gap-count.md",
    "assurance/MP-202-detection-recall.md",
];

fn invalid(message: impl Into<Box<str>>) -> CorpusError {
    CorpusError::new(ErrorCode::Input, message)
}

fn digest_parts(parts: &[Vec<u8>]) -> String {
    let mut digest = Sha256::new();
    for part in parts {
        digest.update((part.len() as u64).to_be_bytes());
        digest.update(part);
    }
    format!("sha256:{:x}", digest.finalize())
}

fn command(root: &Path, args: &[&str]) -> Result<String, CorpusError> {
    let output = Command::new(args[0])
        .args(&args[1..])
        .current_dir(root)
        .output()
        .map_err(|error| invalid(format!("{}: {error}", args.join(" "))))?;
    if !output.status.success() {
        return Err(invalid(format!(
            "{} failed: {}",
            args.join(" "),
            String::from_utf8_lossy(&output.stderr).trim()
        )));
    }
    String::from_utf8(output.stdout)
        .map_err(|error| invalid(format!("{} emitted non-UTF-8: {error}", args[0])))
}

fn full_sha(value: &str) -> bool {
    value.len() == 40
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn full_digest(value: &str) -> bool {
    value.strip_prefix("sha256:").is_some_and(|hex| {
        hex.len() == 64
            && hex
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    })
}

fn normalized_remote(remote: &str) -> String {
    let remote = remote.trim();
    let remote = remote.strip_prefix("git@github.com:").map_or_else(
        || remote.to_owned(),
        |path| format!("https://github.com/{path}"),
    );
    remote
        .trim_end_matches(".git")
        .trim_end_matches('/')
        .to_owned()
}

fn source_revision(root: &Path) -> Result<String, CorpusError> {
    let revision = command(root, &["git", "rev-parse", "HEAD"])?;
    let revision = revision.trim();
    if !full_sha(revision) {
        return Err(invalid("the corpus source revision is unavailable"));
    }
    let status = command(
        root,
        &["git", "status", "--porcelain=v1", "--untracked-files=all"],
    )?;
    if !status.trim().is_empty() {
        return Err(invalid("the corpus source tree is dirty"));
    }
    Ok(revision.to_owned())
}

/// Validate the exact verification-stack attestation before using it as evidence.
pub fn load_verification_stack(
    path: &Path,
    source_remote: &str,
    revision: Option<&str>,
) -> Result<Value, CorpusError> {
    let bytes = fs::read(path).map_err(|error| {
        invalid(format!(
            "verification-stack attestation is unreadable: {error}"
        ))
    })?;
    let value: Value = serde_json::from_slice(&bytes).map_err(|error| {
        invalid(format!(
            "verification-stack attestation is unreadable: {error}"
        ))
    })?;
    if value["schemaVersion"] != "verification-stack-attestation-v1" {
        return Err(invalid(
            "verification-stack attestation has unsupported schemaVersion",
        ));
    }
    for key in ["lockDigest", "executableDigest"] {
        if !value[key].as_str().is_some_and(full_digest) {
            return Err(invalid(format!(
                "verification-stack {key} is not a full sha256 digest"
            )));
        }
    }
    if value["buildProfile"] != "release" {
        return Err(invalid("verification-stack buildProfile must be release"));
    }
    let sources = value["sources"]
        .as_object()
        .filter(|map| !map.is_empty())
        .ok_or_else(|| invalid("verification-stack sources must be a non-empty object"))?;
    for (name, source) in sources {
        if !source["revision"].as_str().is_some_and(full_sha)
            || source["sourceState"] != "clean"
            || source["remote"].as_str().is_none_or(str::is_empty)
        {
            return Err(invalid(format!(
                "verification-stack source {name} is not clean and immutable"
            )));
        }
    }
    let own = sources
        .get("qa-corpus")
        .ok_or_else(|| invalid("verification-stack has no qa-corpus source"))?;
    if revision.is_some_and(|revision| own["revision"] != revision) {
        return Err(invalid(
            "verification-stack qa-corpus revision does not match exporter source",
        ));
    }
    if normalized_remote(own["remote"].as_str().unwrap_or("")) != normalized_remote(source_remote) {
        return Err(invalid(
            "verification-stack qa-corpus remote does not match exporter origin",
        ));
    }
    let capabilities = value["capabilities"]
        .as_array()
        .filter(|items| !items.is_empty())
        .ok_or_else(|| {
            invalid("verification-stack capabilities must be non-empty, unique, and sorted")
        })?;
    let mut sorted = BTreeSet::new();
    for capability in capabilities {
        let Some(capability) = capability.as_str().filter(|value| !value.is_empty()) else {
            return Err(invalid(
                "verification-stack capabilities must be non-empty, unique, and sorted",
            ));
        };
        sorted.insert(capability);
    }
    if sorted.len() != capabilities.len()
        || !capabilities.iter().filter_map(Value::as_str).eq(sorted)
    {
        return Err(invalid(
            "verification-stack capabilities must be non-empty, unique, and sorted",
        ));
    }
    let artifacts = value["artifacts"]
        .as_object()
        .filter(|map| !map.is_empty())
        .ok_or_else(|| invalid("verification-stack artifacts must be a non-empty object"))?;
    for (name, artifact) in artifacts {
        if !artifact.as_str().is_some_and(full_digest) {
            return Err(invalid(format!(
                "verification-stack artifact {name} is not a full sha256 digest"
            )));
        }
    }
    for name in ["node", "rust", "python"] {
        if value["toolchains"][name].as_str().is_none_or(str::is_empty) {
            return Err(invalid(
                "verification-stack toolchains must pin node, rust, and python",
            ));
        }
    }
    Ok(value)
}

/// Return the attested source revision after admitting only committed evidence overlays.
pub fn validate_source_against_stack(root: &Path, stack: &Value) -> Result<String, CorpusError> {
    let head = source_revision(root)?;
    let locked = stack["sources"]["qa-corpus"]["revision"]
        .as_str()
        .ok_or_else(|| invalid("verification-stack has no qa-corpus source revision"))?;
    if head == locked {
        return Ok(locked.to_owned());
    }
    let ancestor = command(root, &["git", "merge-base", locked, &head])?;
    if ancestor.trim() != locked {
        return Err(invalid(
            "qa-corpus evidence overlay does not descend from the attested revision",
        ));
    }
    let commits = command(
        root,
        &["git", "rev-list", "--parents", &format!("{locked}..{head}")],
    )?;
    if commits
        .lines()
        .any(|line| line.split_whitespace().count() != 2)
    {
        return Err(invalid(
            "qa-corpus evidence overlay is not a linear, merge-free chain",
        ));
    }
    let changed = command(root, &["git", "diff", "--name-only", locked, &head])?;
    let unexpected: Vec<_> = changed
        .lines()
        .filter(|path| {
            !path.is_empty()
                && *path != "spec/evidence/measurements"
                && !path.starts_with("spec/evidence/measurements/")
        })
        .collect();
    if !unexpected.is_empty() {
        return Err(invalid(format!(
            "qa-corpus evidence overlay changes non-evidence paths: {}",
            unexpected.join(", ")
        )));
    }
    Ok(locked.to_owned())
}

fn baselines(root: &Path) -> Result<Map<String, Value>, CorpusError> {
    let mut values = Map::new();
    for runner in RUNNERS {
        let path = root.join("baselines").join(format!("{runner}.json"));
        let bytes = fs::read(&path).map_err(|error| {
            invalid(format!(
                "{}: unreadable runner baseline: {error}",
                path.display()
            ))
        })?;
        let value: Value = serde_json::from_slice(&bytes).map_err(|error| {
            invalid(format!(
                "{}: unreadable runner baseline: {error}",
                path.display()
            ))
        })?;
        if value["runner"] != runner
            || value["definition_version"] != "detection-recall-v1"
            || value["rows"].as_array().is_none_or(Vec::is_empty)
        {
            return Err(invalid(format!(
                "{}: invalid runner recall baseline",
                path.display()
            )));
        }
        values.insert(runner.to_owned(), value);
    }
    Ok(values)
}

fn detection_observations(baselines: &Map<String, Value>) -> Result<Vec<Value>, CorpusError> {
    let mut observations = Vec::new();
    let mut seen = BTreeSet::new();
    for runner in RUNNERS {
        for row in baselines[runner]["rows"].as_array().into_iter().flatten() {
            let reached = row["reached"]
                .as_i64()
                .ok_or_else(|| invalid(format!("{runner}: recall row lacks integer counts")))?;
            let population = row["population"]
                .as_i64()
                .ok_or_else(|| invalid(format!("{runner}: recall row lacks integer counts")))?;
            if population < 0 || reached < 0 || reached > population {
                return Err(invalid(format!(
                    "{runner}: invalid recall population {reached}/{population}"
                )));
            }
            let mut dimensions = Map::from_iter([
                ("runner".into(), Value::String(runner.into())),
                ("mode".into(), row["mode"].clone()),
                ("language".into(), row["language"].clone()),
                ("level".into(), row["level"].clone()),
            ]);
            if let Some(family) = row.get("family") {
                dimensions.insert("family".into(), family.clone());
            }
            if dimensions
                .values()
                .any(|value| value.as_str().is_none_or(str::is_empty))
            {
                return Err(invalid(format!(
                    "{runner}: recall row has an empty dimension"
                )));
            }
            let key =
                serde_json::to_string(&dimensions).map_err(|error| invalid(error.to_string()))?;
            if !seen.insert(key) {
                return Err(invalid(format!(
                    "{runner}: duplicate detection.recall dimensions {dimensions:?}"
                )));
            }
            let exclusions = row.get("exclusions").cloned().unwrap_or_else(|| json!([]));
            let Some(exclusions_array) = exclusions.as_array() else {
                return Err(invalid(format!(
                    "{runner}: recall exclusions are not a list"
                )));
            };
            if population == 0 && (reached != 0 || exclusions_array.is_empty()) {
                return Err(invalid(format!(
                    "{runner}: zero recall population must retain exclusions and zero reached"
                )));
            }
            let mut identity = dimensions.clone();
            identity.insert(
                "misses".into(),
                row.get("misses").cloned().unwrap_or_else(|| json!([])),
            );
            identity.insert("exclusions".into(), exclusions);
            let value = if population == 0 {
                Value::Null
            } else {
                let fraction = (reached as f64 / population as f64 * 1_000_000.0).round_ties_even()
                    / 1_000_000.0;
                json!(fraction)
            };
            observations.push(json!({
                "metric":"detection.recall", "planId":"MP-202", "definitionVersion":"detection-recall-v1",
                "state": if population == 0 {"not_computed"} else {"measured"},
                "value":value, "unit":"fraction of seeded failure cases", "shape":"ratio",
                "population":{"examined":population, "matched":reached, "complete":true, "identity":identity},
                "dimensions":dimensions,
            }));
        }
    }
    Ok(observations)
}

fn utc_timestamp() -> String {
    let now = OffsetDateTime::now_utc();
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:03}Z",
        now.year(),
        u8::from(now.month()),
        now.day(),
        now.hour(),
        now.minute(),
        now.second(),
        now.millisecond()
    )
}

/// Build a deterministic collection from derived bounds and both runner baselines.
pub fn build_collection(
    root: &Path,
    stack: &Value,
    revision: &str,
    timestamp: &str,
) -> Result<Value, CorpusError> {
    let cases = discover(root)?;
    let bounds = bounds::derive(root, &cases)?;
    bounds::require_complete(&bounds)?;
    let baselines = baselines(root)?;
    let summary = &bounds["bounds"];
    let gap_count = summary["gap_count"]
        .as_i64()
        .ok_or_else(|| invalid("derived bounds gap_count is not an integer"))?;
    for (runner, baseline) in &baselines {
        if baseline["gap_count"] != gap_count {
            return Err(invalid(format!(
                "{runner}: baseline gap_count {} disagrees with derived {gap_count}",
                baseline["gap_count"]
            )));
        }
    }
    let raw = json!({"bounds":bounds, "runnerBaselines":baselines});
    let raw_bytes = serde_json::to_vec(&raw).map_err(|error| invalid(error.to_string()))?;
    let evidence_digest = digest_parts(&[raw_bytes]);
    let mut observations = vec![json!({
        "metric":"bounds.gap_count", "planId":"MP-201", "definitionVersion":"bounds.gap-count-v1",
        "state":"measured", "value":gap_count, "unit":"mode-language cell", "shape":"count",
        "population":{"examined":summary["declared_cells"], "matched":gap_count, "complete":true, "identity":summary["matrix"]}
    })];
    observations.extend(detection_observations(&baselines)?);
    let config_parts = CONFIG_FILES
        .iter()
        .map(|relative| {
            fs::read(root.join(relative)).map_err(|error| invalid(format!("{relative}: {error}")))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let config_digest = digest_parts(&config_parts);
    let compact_time: String = timestamp
        .chars()
        .filter(|ch| ch.is_ascii_alphanumeric())
        .collect();
    Ok(json!({
        "schemaVersion":2,
        "collectionId":format!("qa-corpus-{compact_time}-{}", &evidence_digest[7..19]),
        "subject":"controlled QA corpus",
        "scope":{"fixtures":cases.len(), "declaredCells":summary["declared_cells"], "runners":RUNNERS},
        "toolIdentity":"qa-corpus measurement exporter",
        "toolVersion":format!("git:{revision}"),
        "configDigest":config_digest,
        "timestamp":timestamp,
        "sourceRevision":revision,
        "environment":{"boundsProducer":"qa-corpus bounds --json --require-complete", "recallProducers":RUNNERS.join(",")},
        "verificationStack":stack,
        "observations":observations,
        "rawEvidence":raw,
    }))
}

/// Export one collection after checking source identity against the attestation.
pub fn export(root: &Path, stack_path: &Path) -> Result<Value, CorpusError> {
    let remote = command(root, &["git", "remote", "get-url", "origin"])?;
    let stack = load_verification_stack(stack_path, remote.trim(), None)?;
    let revision = validate_source_against_stack(root, &stack)?;
    build_collection(root, &stack, &revision, &utc_timestamp())
}

#[cfg(test)]
mod tests {
    use std::{fs, path::Path, process::Command};

    use serde_json::json;

    use super::{
        build_collection, detection_observations, digest_parts, load_verification_stack,
        validate_source_against_stack,
    };

    fn git(root: &Path, args: &[&str]) -> String {
        let output = Command::new("git")
            .args(args)
            .current_dir(root)
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}: {}",
            args.join(" "),
            String::from_utf8_lossy(&output.stderr)
        );
        String::from_utf8(output.stdout).unwrap().trim().to_owned()
    }

    /// Trace: MP-201, MP-202. A measurement evidence overlay preserves the source revision.
    #[test]
    fn evidence_overlay_allows_only_committed_measurements() {
        let scratch = tempfile::tempdir().unwrap();
        let root = scratch.path();
        git(root, &["init", "--quiet"]);
        git(root, &["config", "user.email", "test@example.invalid"]);
        git(root, &["config", "user.name", "Test"]);
        fs::write(root.join("source.rs"), "locked\n").unwrap();
        git(root, &["add", "source.rs"]);
        git(root, &["commit", "--quiet", "-m", "source"]);
        let locked = git(root, &["rev-parse", "HEAD"]);
        let mut stack = attestation();
        stack["sources"]["qa-corpus"]["revision"] = json!(locked);
        let evidence = root.join("spec/evidence/measurements/run.json");
        fs::create_dir_all(evidence.parent().unwrap()).unwrap();
        fs::write(&evidence, "{}\n").unwrap();
        git(root, &["add", "spec/evidence/measurements/run.json"]);
        git(root, &["commit", "--quiet", "-m", "evidence"]);
        assert_eq!(validate_source_against_stack(root, &stack).unwrap(), locked);
        fs::write(root.join("source.rs"), "drifted\n").unwrap();
        git(root, &["add", "source.rs"]);
        git(root, &["commit", "--quiet", "-m", "source drift"]);
        assert!(validate_source_against_stack(root, &stack).is_err());
        fs::write(root.join("untracked.txt"), "dirty\n").unwrap();
        assert!(validate_source_against_stack(root, &stack).is_err());
    }

    fn attestation() -> serde_json::Value {
        json!({
            "schemaVersion":"verification-stack-attestation-v1",
            "lockDigest":format!("sha256:{}", "1".repeat(64)),
            "executableDigest":format!("sha256:{}", "2".repeat(64)),
            "buildProfile":"release",
            "sources":{"qa-corpus":{"revision":"a".repeat(40), "sourceState":"clean", "remote":"https://github.com/agent-ix/qa-corpus"}},
            "capabilities":["fixture.capability"],
            "artifacts":{"fixture":format!("sha256:{}", "3".repeat(64))},
            "toolchains":{"node":"fixture", "rust":"fixture", "python":"fixture"},
        })
    }

    /// Trace: MP-201, MP-202. Unpinned or reordered stack evidence fails closed.
    #[test]
    fn verification_stack_rejects_mutated_identity_and_order() {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("stack.json");
        let original = attestation();
        let remote = "git@github.com:agent-ix/qa-corpus.git";
        fs::write(&path, original.to_string()).unwrap();
        assert_eq!(
            load_verification_stack(&path, remote, Some(&"a".repeat(40))).unwrap(),
            original
        );
        for (name, mutated) in [
            ("schema", {
                let mut value = original.clone();
                value["schemaVersion"] = json!("moving-v2");
                value
            }),
            ("digest", {
                let mut value = original.clone();
                value["lockDigest"] = json!("sha256:short");
                value
            }),
            ("revision", {
                let mut value = original.clone();
                value["sources"]["qa-corpus"]["revision"] = json!("b".repeat(40));
                value
            }),
            ("dirty", {
                let mut value = original.clone();
                value["sources"]["qa-corpus"]["sourceState"] = json!("dirty");
                value
            }),
            ("order", {
                let mut value = original.clone();
                value["capabilities"] = json!(["z", "a"]);
                value
            }),
            ("artifact", {
                let mut value = original.clone();
                value["artifacts"]["fixture"] = json!("moving");
                value
            }),
        ] {
            fs::write(&path, mutated.to_string()).unwrap();
            assert!(
                load_verification_stack(&path, remote, Some(&"a".repeat(40))).is_err(),
                "{name} mutation accepted"
            );
        }
        fs::write(&path, original.to_string()).unwrap();
        assert!(
            load_verification_stack(&path, "https://github.com/other/qa-corpus", None).is_err()
        );
    }

    /// Trace: MP-201, MP-202. Both plans retain their distinct population forms.
    #[test]
    fn collection_derives_gap_and_partitioned_recall() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR"));
        let collection = build_collection(
            root,
            &json!({"schemaVersion":"fixture"}),
            &"a".repeat(40),
            "2026-08-27T00:00:00.000Z",
        )
        .unwrap();
        let observations = collection["observations"].as_array().unwrap();
        let gap = observations
            .iter()
            .filter(|row| row["metric"] == "bounds.gap_count")
            .collect::<Vec<_>>();
        let recall = observations
            .iter()
            .filter(|row| row["metric"] == "detection.recall")
            .collect::<Vec<_>>();
        assert_eq!(gap.len(), 1);
        assert_eq!(gap[0]["value"], 0);
        assert!(!recall.is_empty());
        assert!(recall
            .iter()
            .any(|row| row["dimensions"]["runner"] == "quire-rs"));
        assert!(recall
            .iter()
            .any(|row| row["dimensions"]["runner"] == "quoin"));
        assert_eq!(
            collection["rawEvidence"]["bounds"]["bounds"]["gap_count"],
            0
        );
    }

    /// Trace: MP-202. A zero denominator keeps its exclusion rationale.
    #[test]
    fn zero_population_is_not_computed() {
        let baselines = serde_json::Map::from_iter([
            (
                "quire-rs".into(),
                json!({"rows":[{"reached":0,"population":0,"mode":"m","language":"rust","level":"L2","exclusions":["not applicable"]}]}),
            ),
            ("quoin".into(), json!({"rows":[]})),
        ]);
        let rows = detection_observations(&baselines).unwrap();
        assert_eq!(rows[0]["state"], "not_computed");
        assert!(rows[0]["value"].is_null());
        assert_eq!(
            rows[0]["population"]["identity"]["exclusions"],
            json!(["not applicable"])
        );
    }

    #[test]
    fn digest_frames_each_input() {
        assert_ne!(
            digest_parts(&[b"ab".to_vec(), b"c".to_vec()]),
            digest_parts(&[b"a".to_vec(), b"bc".to_vec()])
        );
    }
}
