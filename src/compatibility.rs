//! Read-only verification of the retained compatibility fixture inputs.
//!
//! The source repositories remain authoritative. This module never writes a
//! retained file or refreshes one from another repository.

use std::{
    collections::{BTreeMap, BTreeSet},
    env, fs,
    path::{Path, PathBuf},
    process::Command,
};

use serde_json::Value;
use sha2::{Digest, Sha256};

use crate::corpus::{CorpusError, ErrorCode};

fn invalid(message: impl Into<Box<str>>) -> CorpusError {
    CorpusError::new(ErrorCode::Input, message)
}

fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn git(repo: &Path, arguments: &[&str]) -> Result<std::process::Output, CorpusError> {
    Command::new("git")
        .arg("-C")
        .arg(repo)
        .args(arguments)
        .output()
        .map_err(|error| {
            invalid(format!(
                "{}: git {}: {error}",
                repo.display(),
                arguments.join(" ")
            ))
        })
}

fn git_success(repo: &Path, arguments: &[&str]) -> Result<Vec<u8>, CorpusError> {
    let output = git(repo, arguments)?;
    if !output.status.success() {
        return Err(invalid(format!(
            "{}: git {} failed: {}",
            repo.display(),
            arguments.join(" "),
            String::from_utf8_lossy(&output.stderr).trim()
        )));
    }
    Ok(output.stdout)
}

fn repo_name(producer: &str) -> &str {
    producer.split_once(' ').map_or(producer, |(name, _)| name)
}

fn checkout(source_root: &Path, repository: &str) -> Result<PathBuf, CorpusError> {
    let name = match repository {
        "agent-ix/quire-contract-ir" => "quire-contract-ir",
        "agent-ix/quire-code-rs" => "quire-code-rs",
        "agent-ix/quoin" => "quoin",
        _ => {
            return Err(invalid(format!(
                "unknown compatibility source repository `{repository}`"
            )))
        }
    };
    let path = source_root.join(name);
    if !path.join(".git").exists() {
        return Err(invalid(format!(
            "source checkout unavailable: {}",
            path.display()
        )));
    }
    Ok(path)
}

/// Locate sibling source checkouts without depending on a workstation path.
pub fn source_root(corpus_root: &Path) -> Result<PathBuf, CorpusError> {
    if let Some(root) = env::var_os("ASSURANCE_SOURCE_ROOT") {
        return Ok(PathBuf::from(root));
    }
    let corpus_root = fs::canonicalize(corpus_root)
        .map_err(|error| invalid(format!("{}: {error}", corpus_root.display())))?;
    for ancestor in corpus_root.ancestors().skip(1) {
        if ["quire-contract-ir", "quire-code-rs", "quoin"]
            .iter()
            .all(|name| ancestor.join(name).is_dir())
        {
            return Ok(ancestor.to_path_buf());
        }
    }
    Err(invalid(
        "ASSURANCE_SOURCE_ROOT is required to locate source checkouts",
    ))
}

/// One repository must resolve to exactly one recorded immutable revision.
pub fn recorded_source_refs(
    index: &Value,
    source_root: &Path,
) -> Result<BTreeMap<PathBuf, String>, CorpusError> {
    let mut revisions: BTreeMap<String, BTreeSet<String>> = BTreeMap::from([
        ("agent-ix/quire-contract-ir".into(), BTreeSet::new()),
        ("agent-ix/quire-code-rs".into(), BTreeSet::new()),
        ("agent-ix/quoin".into(), BTreeSet::new()),
    ]);
    for producer in index["producer_cases"].as_array().into_iter().flatten() {
        let Some(name) = producer["producer"].as_str().map(repo_name) else {
            continue;
        };
        let Some(revision) = producer["revision"].as_str() else {
            continue;
        };
        if let Some(candidates) = revisions.get_mut(name) {
            candidates.insert(revision.to_owned());
        }
    }
    let mut selected = BTreeMap::new();
    for (name, candidates) in revisions {
        if candidates.len() != 1 {
            return Err(invalid(format!(
                "committed corpus records {} revisions for {name}: {candidates:?}",
                candidates.len()
            )));
        }
        let path = checkout(source_root, &name)?;
        selected.insert(path, candidates.into_iter().next().expect("one revision"));
    }
    Ok(selected)
}

/// Prove every recorded revision is reachable from its published main ref.
pub fn require_published_source_refs(refs: &BTreeMap<PathBuf, String>) -> Result<(), CorpusError> {
    for (repo, revision) in refs {
        let output = git(
            repo,
            &["merge-base", "--is-ancestor", revision, "origin/main"],
        )?;
        match output.status.code() {
            Some(0) => {}
            Some(1) => {
                return Err(invalid(format!(
                    "recorded source revision is not reachable from origin/main: {} at {revision}",
                    repo.display()
                )))
            }
            _ => {
                return Err(invalid(format!(
                "cannot verify recorded source revision against origin/main: {} at {revision}: {}",
                repo.display(),
                String::from_utf8_lossy(&output.stderr).trim()
            )))
            }
        }
    }
    Ok(())
}

fn read_at(repo: &Path, path: &str, revision: &str) -> Result<Vec<u8>, CorpusError> {
    git_success(repo, &["show", &format!("{revision}:{path}")])
}

fn revision<'a>(refs: &'a BTreeMap<PathBuf, String>, repo: &Path) -> Result<&'a str, CorpusError> {
    refs.get(repo).map(String::as_str).ok_or_else(|| {
        invalid(format!(
            "no recorded source revision for {}",
            repo.display()
        ))
    })
}

fn retained(root: &Path, relative: &str) -> Result<Vec<u8>, CorpusError> {
    let path = Path::new(relative);
    if path.is_absolute()
        || path
            .components()
            .any(|component| matches!(component, std::path::Component::ParentDir))
    {
        return Err(invalid(format!("unsafe retained path `{relative}`")));
    }
    let compatibility = fs::canonicalize(root.join("compatibility"))
        .map_err(|error| invalid(format!("compatibility root: {error}")))?;
    let candidate = compatibility.join(path);
    let metadata = fs::symlink_metadata(&candidate)
        .map_err(|error| invalid(format!("compatibility/{relative}: {error}")))?;
    if !metadata.is_file() {
        return Err(invalid(format!(
            "compatibility/{relative}: expected a regular file"
        )));
    }
    let resolved = fs::canonicalize(&candidate)
        .map_err(|error| invalid(format!("compatibility/{relative}: {error}")))?;
    if !resolved.starts_with(&compatibility) {
        return Err(invalid(format!(
            "compatibility/{relative}: resolves outside corpus"
        )));
    }
    fs::read(candidate).map_err(|error| invalid(format!("compatibility/{relative}: {error}")))
}

fn compact(value: &Value) -> Result<Vec<u8>, CorpusError> {
    serde_json::to_vec(value).map_err(|error| invalid(error.to_string()))
}

/// Verify immutable sources and every retained input without writing a file.
pub fn check(root: &Path, sources: &Path) -> Result<String, CorpusError> {
    let index_path = root.join("compatibility/corpus.json");
    let bytes = fs::read(&index_path)
        .map_err(|error| invalid(format!("{}: {error}", index_path.display())))?;
    let index: Value = serde_json::from_slice(&bytes)
        .map_err(|error| invalid(format!("{}: {error}", index_path.display())))?;
    let refs = recorded_source_refs(&index, sources)?;
    require_published_source_refs(&refs)?;
    let contract_ir = checkout(sources, "agent-ix/quire-contract-ir")?;
    let mut legacy = BTreeMap::new();
    for case in index["cases"].as_array().into_iter().flatten() {
        let id = case["id"]
            .as_str()
            .ok_or_else(|| invalid("compatibility case has no id"))?;
        let relative = case["retained_path"]
            .as_str()
            .ok_or_else(|| invalid(format!("{id}: no retained_path")))?;
        let held = retained(root, relative)?;
        if case["derivation"].is_null()
            && case["origin"]["repository"] == "agent-ix/quire-contract-ir"
        {
            let source = case["origin"]["path"]
                .as_str()
                .ok_or_else(|| invalid(format!("{id}: no origin path")))?;
            let revision = revision(&refs, &contract_ir)?;
            let original = read_at(&contract_ir, source, revision)?;
            if original != held || case["origin"]["recorded_sha256"] != digest(&original) {
                return Err(invalid(format!(
                    "{id}: retained bytes differ from recorded contract-ir source"
                )));
            }
            let record_id = source
                .strip_prefix("evidence/")
                .and_then(|path| path.strip_suffix("/manifest.json"))
                .ok_or_else(|| invalid(format!("{id}: unexpected contract-ir source path")))?;
            let checksums = read_at(
                &contract_ir,
                &format!("evidence/{record_id}.sha256"),
                revision,
            )?;
            let checksums = String::from_utf8(checksums).map_err(|error| {
                invalid(format!("{id}: source checksums are not UTF-8: {error}"))
            })?;
            let source_digest = checksums
                .lines()
                .find(|line| line.ends_with(source))
                .and_then(|line| line.split_whitespace().next())
                .ok_or_else(|| invalid(format!("{id}: source records no manifest digest")))?;
            if source_digest != digest(&original) {
                return Err(invalid(format!(
                    "{id}: source manifest digest disagrees with its checksum file"
                )));
            }
            legacy.insert(id.to_owned(), original);
        }
    }
    verify_derived(root, &index, &legacy)?;
    for producer in index["producer_cases"].as_array().into_iter().flatten() {
        let id = producer["id"]
            .as_str()
            .ok_or_else(|| invalid("producer has no id"))?;
        let name = producer["producer"]
            .as_str()
            .ok_or_else(|| invalid(format!("{id}: no producer")))?;
        let repo = checkout(sources, repo_name(name))?;
        let source = producer["path"]
            .as_str()
            .ok_or_else(|| invalid(format!("{id}: no source path")))?;
        let relative = producer["retained_path"]
            .as_str()
            .ok_or_else(|| invalid(format!("{id}: no retained_path")))?;
        let original = read_at(&repo, source, revision(&refs, &repo)?)?;
        let held = retained(root, relative)?;
        if original != held || producer["source_sha256"] != digest(&original) {
            return Err(invalid(format!(
                "{id}: retained bytes differ from recorded producer source"
            )));
        }
    }
    for artifact in index["chain"]["artifacts"].as_array().into_iter().flatten() {
        let relative = artifact["retained_path"]
            .as_str()
            .ok_or_else(|| invalid("chain artifact has no retained_path"))?;
        retained(root, relative)?;
    }
    Ok("compatibility corpus reproduces from recorded published sources".into())
}

fn verify_derived(
    root: &Path,
    index: &Value,
    legacy: &BTreeMap<String, Vec<u8>>,
) -> Result<(), CorpusError> {
    let base = legacy
        .get("legacy-v1-passing")
        .ok_or_else(|| invalid("no recorded legacy-v1-passing source"))?;
    let parsed: Value = serde_json::from_slice(base)
        .map_err(|error| invalid(format!("legacy-v1-passing: {error}")))?;
    let mut expected = BTreeMap::new();
    for (id, status) in [
        ("derived-failed", "fail"),
        ("derived-unavailable", "unavailable"),
        ("derived-not-computed", "not_computed"),
    ] {
        let mut value = parsed.clone();
        value["checks"][0]["status"] = Value::String(status.into());
        expected.insert(id, compact(&value)?);
    }
    let mut malformed = parsed.clone();
    malformed
        .as_object_mut()
        .ok_or_else(|| invalid("legacy source is not an object"))?
        .remove("collector");
    expected.insert("derived-malformed", compact(&malformed)?);
    let revision = parsed["subjectRevision"]
        .as_str()
        .ok_or_else(|| invalid("legacy source has no subjectRevision"))?;
    let original = String::from_utf8(base.clone())
        .map_err(|error| invalid(format!("legacy source is not UTF-8: {error}")))?;
    let tampered = original.replacen(revision, &"0".repeat(40), 1);
    if tampered == original {
        return Err(invalid("tampered derivation changed nothing"));
    }
    expected.insert("derived-tampered", tampered.into_bytes());
    expected.insert("derived-unreadable", b"not json at all\n".to_vec());
    let mut incompatible = parsed;
    incompatible["schemaVersion"] = Value::String("quire.pgm01-evidence/v99".into());
    expected.insert("derived-incompatible-version", compact(&incompatible)?);
    let source = root.join("compatibility/sources/pgm01-v2.json");
    let original =
        fs::read(&source).map_err(|error| invalid(format!("{}: {error}", source.display())))?;
    let mut stale: Value = serde_json::from_slice(&original)
        .map_err(|error| invalid(format!("{}: {error}", source.display())))?;
    stale["historicalDisposition"] = Value::String("retracted".into());
    expected.insert("derived-stale", compact(&stale)?);
    for case in index["cases"].as_array().into_iter().flatten() {
        let id = case["id"]
            .as_str()
            .ok_or_else(|| invalid("compatibility case has no id"))?;
        let Some(derived) = expected.get(id) else {
            continue;
        };
        let relative = case["retained_path"]
            .as_str()
            .ok_or_else(|| invalid(format!("{id}: no retained_path")))?;
        if retained(root, relative)? != *derived {
            return Err(invalid(format!(
                "{id}: retained derived bytes disagree with its recorded source mutation"
            )));
        }
        if id == "derived-stale" && case["origin"]["recorded_sha256"] != digest(&original) {
            return Err(invalid(
                "derived-stale: source digest disagrees with corpus index",
            ));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::{collections::BTreeMap, fs, path::Path, process::Command};

    use serde_json::Value;

    use super::{require_published_source_refs, verify_derived};

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

    /// Trace: EA FR-011. Only a recorded revision published on origin/main is admissible.
    #[test]
    fn source_ref_must_be_reachable_from_published_main() {
        let scratch = tempfile::tempdir().unwrap();
        let root = scratch.path();
        git(root, &["init", "--quiet"]);
        git(root, &["config", "user.email", "test@example.invalid"]);
        git(root, &["config", "user.name", "Test"]);
        fs::write(root.join("source.txt"), "recorded\n").unwrap();
        git(root, &["add", "source.txt"]);
        git(root, &["commit", "--quiet", "-m", "published"]);
        let recorded = git(root, &["rev-parse", "HEAD"]);
        git(root, &["update-ref", "refs/remotes/origin/main", &recorded]);
        let mut refs = BTreeMap::from([(root.to_path_buf(), recorded)]);
        require_published_source_refs(&refs).unwrap();
        fs::write(root.join("source.txt"), "local only\n").unwrap();
        git(root, &["add", "source.txt"]);
        git(root, &["commit", "--quiet", "-m", "unpublished"]);
        refs.insert(root.to_path_buf(), git(root, &["rev-parse", "HEAD"]));
        let error = require_published_source_refs(&refs).unwrap_err();
        assert!(error.to_string().contains("not reachable from origin/main"));
        refs.insert(root.to_path_buf(), "f".repeat(40));
        let error = require_published_source_refs(&refs).unwrap_err();
        assert!(error
            .to_string()
            .contains("cannot verify recorded source revision"));
    }

    /// Trace: EA FR-011. Existing derived fixture inputs reproduce in memory.
    #[test]
    fn retained_derived_inputs_match_their_named_mutations() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR"));
        let index: Value =
            serde_json::from_slice(&fs::read(root.join("compatibility/corpus.json")).unwrap())
                .unwrap();
        let base = fs::read(root.join("compatibility/records/legacy-v1-passing.json")).unwrap();
        let legacy = BTreeMap::from([("legacy-v1-passing".into(), base)]);
        verify_derived(root, &index, &legacy).unwrap();
    }
}
