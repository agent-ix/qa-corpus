//! Case invocation and payload grading for the controlled QA corpus.

use std::{collections::BTreeMap, fs, path::Path, process::Command};

use serde_json::{json, Value};

use crate::corpus::{controls_by_case, Case, CorpusError, ErrorCode};

const REQUIRED_CAPABILITIES: &[&str] = &[
    "action_guidance.structured",
    "binding_census",
    "binding_census.self_named",
    "binding_census.tagged",
    "declaration_origins",
    "metrics_envelope",
    "property_spans.safe_refusal",
];

fn invalid(message: impl Into<Box<str>>) -> CorpusError {
    CorpusError::new(ErrorCode::Input, message)
}

/// Run the authored command over the checked-in input without copying it.
pub fn run_case(root: &Path, case: &Case, quire: &Path) -> Result<Value, CorpusError> {
    let (tokens, assignments) = invocation(case)?;
    let output = Command::new(quire)
        .args(tokens.iter().skip(1))
        .envs(assignments)
        .current_dir(root)
        .output()
        .map_err(|error| {
            invalid(format!(
                "{}: invocation failed: {error}",
                case.directory.display()
            ))
        })?;
    if !output.status.success() || output.stdout.is_empty() {
        return Err(invalid(format!(
            "{}: invocation failed: {}",
            case.directory.display(),
            String::from_utf8_lossy(&output.stderr).trim()
        )));
    }
    serde_json::from_slice(&output.stdout).map_err(|error| {
        invalid(format!(
            "{}: invocation emitted invalid JSON: {error}",
            case.directory.display()
        ))
    })
}

fn invocation(case: &Case) -> Result<(Vec<String>, BTreeMap<String, String>), CorpusError> {
    let reproduce = case.effective["reproduce"].as_str().ok_or_else(|| {
        invalid(format!(
            "{}: reproduce is missing",
            case.directory.display()
        ))
    })?;
    let mut tokens = reproduce.split_whitespace().peekable();
    let mut assignments = BTreeMap::new();
    while let Some(token) = tokens.peek().copied() {
        let Some((name, value)) = token.split_once('=') else {
            break;
        };
        let valid = name
            .chars()
            .next()
            .is_some_and(|first| first.is_ascii_alphabetic() || first == '_')
            && name
                .chars()
                .all(|ch| ch.is_ascii_alphanumeric() || ch == '_');
        if !valid {
            break;
        }
        assignments.insert(name.to_owned(), value.to_owned());
        tokens.next();
    }
    let executable = tokens
        .next()
        .ok_or_else(|| invalid("reproduce names no executable"))?;
    if executable != "quire" {
        return Err(invalid(format!(
            "{}: reproduce must invoke quire",
            case.directory.display()
        )));
    }
    Ok((
        std::iter::once(executable.to_owned())
            .chain(tokens.map(str::to_owned))
            .collect(),
        assignments,
    ))
}

/// Run Quire's structural validator over the same authored scope as a case.
pub fn run_validate(root: &Path, case: &Case, quire: &Path) -> Result<String, CorpusError> {
    let (tokens, assignments) = invocation(case)?;
    let scope = tokens
        .windows(2)
        .find(|pair| pair[0] == "--scope")
        .map(|pair| pair[1].as_str())
        .ok_or_else(|| {
            invalid(format!(
                "{}: reproduce has no --scope",
                case.directory.display()
            ))
        })?;
    let output = Command::new(quire)
        .args(["validate", "--scope", scope, "spec/tests.md"])
        .envs(assignments)
        .current_dir(root)
        .output()
        .map_err(|error| {
            invalid(format!(
                "{}: validate invocation failed: {error}",
                case.directory.display()
            ))
        })?;
    Ok(format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    ))
}

/// Collect the exact non-Quire witness channels declared by this corpus.
pub fn inspect_external(root: &Path, case: &Case, quoin: &Path) -> Result<Value, CorpusError> {
    let config_path = root.join("config/external-channel.json");
    let config_bytes = fs::read(&config_path)
        .map_err(|error| invalid(format!("{}: {error}", config_path.display())))?;
    let config: Value = serde_json::from_slice(&config_bytes)
        .map_err(|error| invalid(format!("{}: {error}", config_path.display())))?;
    let repo = fs::canonicalize(root.join(&case.directory).join("input"))
        .map_err(|error| invalid(format!("{}: {error}", case.directory.display())))?;
    let repo = repo.to_string_lossy();
    let mut observations = Vec::new();
    for kind in ["mock-injection-observed", "gate-that-gates-nothing"] {
        let tokens = config["channels"][kind]["command"]
            .as_array()
            .ok_or_else(|| invalid(format!("external channel `{kind}` has no command")))?;
        let args = tokens
            .iter()
            .map(|token| {
                token
                    .as_str()
                    .map(|token| token.replace("{repo}", &repo))
                    .ok_or_else(|| {
                        invalid(format!("external channel `{kind}` has non-string argument"))
                    })
            })
            .collect::<Result<Vec<_>, _>>()?;
        let output = Command::new(quoin)
            .args(&args)
            .current_dir(root)
            .env("CI", "1")
            .output()
            .map_err(|error| invalid(format!("{kind}: producer failed: {error}")))?;
        if !output.status.success() {
            return Err(invalid(format!(
                "{kind}: producer failed: {}",
                String::from_utf8_lossy(&output.stderr).trim()
            )));
        }
        let payload: Value = serde_json::from_slice(&output.stdout)
            .map_err(|error| invalid(format!("{kind}: producer emitted invalid JSON: {error}")))?;
        if kind == "mock-injection-observed" {
            for item in array(&payload, "injections") {
                let injects = item
                    .get("injects")
                    .filter(|value| !value.is_null())
                    .cloned()
                    .unwrap_or_else(|| json!([]));
                observations.push(json!({
                    "kind": "mock-injection-observed", "path": item["path"],
                    "line": item["line"], "symbol": item["symbol"],
                    "injects": injects,
                }));
            }
        } else {
            for item in array(&payload, "findings") {
                if item["kind"] == "gate-that-gates-nothing" {
                    observations.push(
                        json!({"kind": item["kind"], "obligation": item["obligation"],
                        "path": item["path"], "line": item["line"]}),
                    );
                }
            }
        }
    }
    observations.sort_by(|left, right| {
        let key = |item: &Value| {
            (
                item["kind"].as_str().unwrap_or("").to_owned(),
                item["path"].as_str().unwrap_or("").to_owned(),
                item["line"].as_u64().unwrap_or(0),
            )
        };
        key(left).cmp(&key(right))
    });
    Ok(Value::Array(observations))
}

/// One complete verification run over the static detection corpus.
#[derive(Debug)]
pub struct Summary {
    /// Number of cases whose authored command ran successfully.
    pub ran: usize,
    /// Total detection cases discovered.
    pub total: usize,
    /// Number of failure/control pairs graded.
    pub pairs: usize,
    /// Case and differential mismatches.
    pub failures: Vec<String>,
    /// Forward blocks still failing while their ticket is pending.
    pub pending: Vec<(String, String, Vec<String>)>,
    /// Tickets whose forward block has begun to hold.
    pub stale: Vec<(String, String)>,
    /// Provenance of the binary under test.
    pub engine: String,
}

/// Execute every authored detection case and grade its live and forward claims.
pub fn verify(root: &Path, quire: &Path, quoin: Option<&Path>) -> Result<Summary, CorpusError> {
    let all = crate::corpus::discover(root)?;
    let engine = check_engine(root, &all, quire)?;
    let cases: Vec<_> = all
        .into_iter()
        .filter(|case| case.effective["mode"] != "reporting")
        .collect();
    let mut summary = Summary {
        ran: 0,
        total: cases.len(),
        pairs: 0,
        failures: Vec::new(),
        pending: Vec::new(),
        stale: Vec::new(),
        engine,
    };
    let mut payloads = BTreeMap::new();
    let mut validations = BTreeMap::new();
    for case in &cases {
        let meta = &case.effective;
        let id = meta["id"].as_str().unwrap_or("unknown case");
        let language = meta["language"].as_str().unwrap_or("");
        let name = format!(
            "{id} ({})",
            meta["issue_ref"].as_str().unwrap_or("no issue")
        );
        let live = crate::corpus::load_yaml(&root.join(&case.expectation))?;
        let forward = if meta["pending"].as_str().is_some() {
            Some(crate::corpus::load_yaml(
                &root.join(&case.directory).join("expect-pending.yaml"),
            )?)
        } else {
            None
        };
        let mut payload = match run_case(root, case, quire) {
            Ok(payload) => payload,
            Err(error) => {
                summary.failures.push(format!("{name}: {error}"));
                continue;
            }
        };
        summary.ran += 1;
        let needs_external = live.get("external_observations").is_some()
            || forward
                .as_ref()
                .is_some_and(|block| block.get("external_observations").is_some());
        if needs_external {
            match quoin {
                Some(quoin) => match inspect_external(root, case, quoin) {
                    Ok(observations) => payload["external_observations"] = observations,
                    Err(error) => summary.failures.push(format!("{name}: {error}")),
                },
                None => summary
                    .failures
                    .push(format!("{name}: external observations require QUOIN")),
            }
        }
        let needs_validate = |block: &Value| {
            !array(block, "validate_contains").is_empty()
                || !array(block, "validate_absent").is_empty()
        };
        let validation = if needs_validate(&live) || forward.as_ref().is_some_and(needs_validate) {
            match run_validate(root, case, quire) {
                Ok(output) => Some(output),
                Err(error) => {
                    summary.failures.push(format!("{name}: {error}"));
                    None
                }
            }
        } else {
            None
        };
        let mine = grade_with_validate(&live, &payload, validation.as_deref());
        summary
            .failures
            .extend(mine.into_iter().map(|failure| format!("{name}: {failure}")));
        if let (Some(ticket), Some(forward)) = (meta["pending"].as_str(), forward.as_ref()) {
            let ahead = grade_with_validate(forward, &payload, validation.as_deref());
            if ahead.is_empty() {
                summary.stale.push((id.to_owned(), ticket.to_owned()));
            } else {
                summary
                    .pending
                    .push((id.to_owned(), ticket.to_owned(), ahead));
            }
        }
        let key = (id.to_owned(), language.to_owned());
        payloads.insert(key.clone(), payload);
        if let Some(output) = validation {
            validations.insert(key, output);
        }
    }
    let declaration = crate::corpus::load_yaml(&root.join("corpus.yaml"))?;
    let (pairs, failures) = differential(
        root,
        &declaration,
        &cases,
        &payloads,
        &validations,
        Some(quire),
    )?;
    summary.pairs = pairs;
    summary.failures.extend(failures);
    Ok(summary)
}

/// Check a real case payload before accepting a CLI as the corpus subject.
pub fn check_engine(root: &Path, cases: &[Case], quire: &Path) -> Result<String, CorpusError> {
    let sample = cases
        .iter()
        .find(|case| case.effective["mode"] != "reporting")
        .ok_or_else(|| invalid("verify: the corpus has no cases to probe with"))?;
    let payload = run_case(root, sample, quire)?;
    let engine = payload
        .get("engine")
        .and_then(Value::as_object)
        .ok_or_else(|| {
            invalid(format!(
                "verify: {} emits no engine provenance block",
                quire.display()
            ))
        })?;
    let capabilities: Vec<_> = engine
        .get("capabilities")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    let missing: Vec<_> = REQUIRED_CAPABILITIES
        .iter()
        .copied()
        .filter(|capability| !capabilities.contains(capability))
        .collect();
    if !missing.is_empty() {
        return Err(invalid(format!(
            "verify: {} lacks required capability token(s): {}",
            quire.display(),
            missing.join(", ")
        )));
    }
    Ok(format!(
        "engine {}",
        engine
            .get("version")
            .and_then(Value::as_str)
            .unwrap_or("unreported")
    ))
}

/// Validate the declared witness-channel restriction before grading pairs.
pub fn witness_channels(declaration: &Value) -> Result<BTreeMap<String, Vec<String>>, CorpusError> {
    let witness = declaration["witness_channels"]
        .as_object()
        .ok_or_else(|| invalid("corpus.yaml declares no witness_channels"))?;
    if witness.is_empty() {
        return Err(invalid("corpus.yaml declares no witness_channels"));
    }
    let families: std::collections::BTreeSet<_> = declaration["mode_families"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    let supported = [
        "backed",
        "total",
        "diagnostic_reasons",
        "absent_diagnostic_reasons",
        "diagnostic_paths",
        "diagnostic_lines",
        "diagnostic_message_contains",
        "binding_census",
        "metrics",
        "no_symbol_rows",
        "unbacked_rows",
        "groups",
        "untracked_symbols",
        "validate_contains",
        "validate_absent",
        "suspicions",
        "absent_suspicions",
        "external_observations",
    ];
    let mut result = BTreeMap::new();
    for (mode, channels) in witness {
        if !families.contains(mode.as_str()) {
            return Err(invalid(format!(
                "witness_channels declares `{mode}`, which mode_families does not"
            )));
        }
        let channels = channels
            .as_array()
            .filter(|channels| !channels.is_empty())
            .ok_or_else(|| invalid(format!("witness_channels.{mode} must be a nonempty list")))?;
        let mut names = Vec::new();
        for channel in channels {
            let name = channel
                .as_str()
                .ok_or_else(|| invalid(format!("witness_channels.{mode} contains a non-string")))?;
            if !supported.contains(&name) {
                return Err(invalid(format!(
                    "witness_channels.{mode} names `{name}`, which this reader cannot grade"
                )));
            }
            names.push(name.to_owned());
        }
        result.insert(mode.to_owned(), names);
    }
    for family in families {
        if !result.contains_key(family) {
            return Err(invalid(format!(
                "mode_families declares `{family}` with no witness_channels entry"
            )));
        }
    }
    Ok(result)
}

/// Grade every failure against every healthy control and its mode channels.
/// The output is the graded pair count and named mismatches.
pub fn differential(
    root: &Path,
    declaration: &Value,
    cases: &[Case],
    payloads: &BTreeMap<(String, String), Value>,
    validations: &BTreeMap<(String, String), String>,
    quire: Option<&Path>,
) -> Result<(usize, Vec<String>), CorpusError> {
    let channels = witness_channels(declaration)?;
    let controls = controls_by_case(cases);
    let behaviour_change: std::collections::BTreeSet<_> = declaration["behaviour_change_tickets"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    let mut failures = Vec::new();
    let mut graded = 0;
    for case in cases {
        let meta = &case.effective;
        if meta["kind"] != "failure" {
            continue;
        }
        let Some(id) = meta["id"].as_str() else {
            continue;
        };
        let language = meta["language"].as_str().unwrap_or("");
        let Some(partners) = controls.get(&(id.to_owned(), language.to_owned())) else {
            continue;
        };
        let live = crate::corpus::load_yaml(&root.join(&case.expectation))?;
        let forward = if meta["pending"]
            .as_str()
            .is_some_and(|ticket| behaviour_change.contains(ticket))
        {
            Some(crate::corpus::load_yaml(
                &root.join(&case.directory).join("expect-pending.yaml"),
            )?)
        } else {
            None
        };
        for control in partners {
            let other_id = control.effective["id"].as_str().unwrap_or("");
            let Some(healthy) = payloads.get(&(other_id.to_owned(), language.to_owned())) else {
                failures.push(format!("{id}: control {other_id} produced no payload"));
                continue;
            };
            graded += 1;
            let needs_validate = !array(&live, "validate_contains").is_empty()
                || !array(&live, "validate_absent").is_empty()
                || forward.as_ref().is_some_and(|block| {
                    !array(block, "validate_contains").is_empty()
                        || !array(block, "validate_absent").is_empty()
                });
            let validation_output = if let Some(cached) =
                validations.get(&(other_id.to_owned(), language.to_owned()))
            {
                Some(cached.clone())
            } else if needs_validate {
                let Some(quire) = quire else {
                    failures.push(format!("{id}: control {other_id} has no validate output"));
                    continue;
                };
                match run_validate(root, control, quire) {
                    Ok(output) => Some(output),
                    Err(error) => {
                        failures.push(format!("{id}: control {other_id} validate failed: {error}"));
                        continue;
                    }
                }
            } else {
                None
            };
            let validate = validation_output.as_deref();
            if grade_with_validate(&live, healthy, validate).is_empty() {
                failures.push(format!(
                    "{id}: expect.yaml holds against control {other_id} (FR-065-AC-42)"
                ));
            }
            if let Some(forward) = forward.as_ref() {
                if !grade_with_validate(forward, healthy, validate).is_empty() {
                    failures.push(format!("{id}: behavior-change forward block does not hold against control {other_id}"));
                }
            }
            let mode = meta["mode"].as_str().unwrap_or("");
            let witness = channels
                .get(mode)
                .ok_or_else(|| invalid(format!("{id}: no witness channels for mode `{mode}`")))?;
            let mut restricted = serde_json::Map::new();
            for key in witness {
                if let Some(value) = live.get(key) {
                    restricted.insert(key.clone(), value.clone());
                }
            }
            if restricted.is_empty() {
                failures.push(format!(
                    "{id}: expect.yaml names no `{mode}` witness channel (FR-065-AC-46)"
                ));
            } else if grade_with_validate(&Value::Object(restricted), healthy, validate).is_empty()
            {
                failures.push(format!(
                    "{id}: witness channels do not separate control {other_id} (FR-065-AC-46)"
                ));
            }
        }
    }
    if graded == 0 {
        failures.push("no failure/control pair was graded".into());
    }
    Ok((graded, failures))
}

fn array<'a>(value: &'a Value, key: &str) -> &'a [Value] {
    value
        .get(key)
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .unwrap_or(&[])
}

fn diagnostic<'a>(payload: &'a Value, key: &str) -> Option<&'a Value> {
    let (declaration, reason) = key.rsplit_once('/').unwrap_or(("", key));
    array(payload, "diagnostics").iter().find(|item| {
        item["reason"] == reason && (declaration.is_empty() || item["declaration"] == declaration)
    })
}

fn finding_text(finding: &Value) -> String {
    [
        "message",
        "evidence",
        "subject",
        "change_target",
        "changeTarget",
        "remedy",
        "next_diagnostic_step",
        "nextDiagnosticStep",
    ]
    .iter()
    .filter_map(|field| finding.get(*field).and_then(Value::as_str))
    .map(str::trim)
    .filter(|value| !value.is_empty())
    .collect::<Vec<_>>()
    .join(" ")
}

fn project(value: &Value, fields: &[&str]) -> Value {
    let mut projected = serde_json::Map::new();
    for field in fields {
        projected.insert(
            (*field).to_owned(),
            value.get(*field).cloned().unwrap_or(Value::Null),
        );
    }
    Value::Object(projected)
}

fn compare_projected(
    expect: &Value,
    payload: &Value,
    key: &str,
    fields: &[&str],
    errors: &mut Vec<String>,
) {
    let Some(wanted) = expect.get(key) else {
        return;
    };
    let actual: Vec<_> = array(payload, key)
        .iter()
        .map(|entry| project(entry, fields))
        .collect();
    if *wanted != Value::Array(actual.clone()) {
        errors.push(format!(
            "{key} expected {wanted}, got {}",
            Value::Array(actual)
        ));
    }
}

/// Grade one expectation block. Each optional field is independent; omission
/// makes no assertion and an authored empty exact list still makes one.
pub fn grade(expect: &Value, payload: &Value) -> Vec<String> {
    grade_with_validate(expect, payload, None)
}

/// Grade a block with the `quire validate` output for the input being checked.
pub fn grade_with_validate(
    expect: &Value,
    payload: &Value,
    validate_output: Option<&str>,
) -> Vec<String> {
    let mut errors = Vec::new();
    let needs_validate = !array(expect, "validate_contains").is_empty()
        || !array(expect, "validate_absent").is_empty();
    if needs_validate && validate_output.is_none() {
        errors.push("validate output was not produced".into());
    }
    if let Some(output) = validate_output {
        for fragment in array(expect, "validate_contains")
            .iter()
            .filter_map(Value::as_str)
        {
            if !output.contains(fragment) {
                errors.push(format!("validate output lacks {fragment:?}"));
            }
        }
        for fragment in array(expect, "validate_absent")
            .iter()
            .filter_map(Value::as_str)
        {
            if output.contains(fragment) {
                errors.push(format!("validate output carries {fragment:?}"));
            }
        }
    }
    for key in ["backed", "total"] {
        if let Some(wanted) = expect.get(key) {
            if payload["totals"][key] != *wanted {
                errors.push(format!(
                    "{key} expected {wanted}, got {}",
                    payload["totals"][key]
                ));
            }
        }
    }
    let mut reasons = Vec::new();
    for item in array(payload, "diagnostics") {
        if let Some(reason) = item["reason"].as_str() {
            reasons.push(reason.to_owned());
            if let Some(declaration) = item["declaration"].as_str() {
                reasons.push(format!("{declaration}/{reason}"));
            }
        }
    }
    for wanted in array(expect, "diagnostic_reasons")
        .iter()
        .filter_map(Value::as_str)
    {
        if !reasons.iter().any(|reason| reason == wanted) {
            errors.push(format!("`{wanted}` did not fire"));
        }
    }
    for absent in array(expect, "absent_diagnostic_reasons")
        .iter()
        .filter_map(Value::as_str)
    {
        if reasons.iter().any(|reason| reason == absent) {
            errors.push(format!("`{absent}` fired on input that must stay silent"));
        }
    }
    for (key, field) in [("diagnostic_paths", "path"), ("diagnostic_lines", "line")] {
        if let Some(wanted) = expect[key].as_object() {
            for (reason, value) in wanted {
                let actual = diagnostic(payload, reason)
                    .and_then(|item| item.get(field))
                    .unwrap_or(&Value::Null);
                let suffix_match = field == "path"
                    && value
                        .as_str()
                        .zip(actual.as_str())
                        .is_some_and(|(wanted, actual)| {
                            !Path::new(wanted).is_absolute() && Path::new(actual).ends_with(wanted)
                        });
                if actual != value && !suffix_match {
                    errors.push(format!("{reason} {field} expected {value}, got {actual}"));
                }
            }
        }
    }
    if let Some(wanted) = expect["diagnostic_message_contains"].as_object() {
        for (reason, fragments) in wanted {
            let Some(fragments) = fragments.as_array() else {
                errors.push(format!(
                    "diagnostic_message_contains.{reason} takes a list of substrings"
                ));
                continue;
            };
            let text = diagnostic(payload, reason)
                .map(finding_text)
                .unwrap_or_default();
            for fragment in fragments.iter().filter_map(Value::as_str) {
                if !text.contains(fragment) {
                    errors.push(format!("{reason} finding text lacks {fragment:?}"));
                }
            }
        }
    }
    compare_projected(
        expect,
        payload,
        "unbacked_rows",
        &["document", "row_id", "target_ids"],
        &mut errors,
    );
    compare_projected(
        expect,
        payload,
        "untracked_symbols",
        &["symbol", "trace_id", "path"],
        &mut errors,
    );
    compare_projected(
        expect,
        payload,
        "groups",
        &["document", "target", "backed", "total"],
        &mut errors,
    );
    if let Some(wanted) = expect.get("external_observations") {
        if payload.get("external_observations") != Some(wanted) {
            errors.push(format!(
                "external_observations expected {wanted}, got {}",
                payload["external_observations"]
            ));
        }
    }
    if let Some(wanted) = expect.get("no_symbol_rows") {
        let mut actual = array(payload, "no_symbol_rows")
            .iter()
            .filter_map(|row| row["row_id"].as_str())
            .collect::<Vec<_>>();
        actual.sort();
        let mut wanted = wanted
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .collect::<Vec<_>>();
        wanted.sort();
        if actual != wanted {
            errors.push(format!(
                "no_symbol_rows expected {wanted:?}, got {actual:?}"
            ));
        }
    }
    for wanted in array(expect, "binding_census") {
        let language = wanted["language"].as_str().unwrap_or("");
        let found = array(payload, "binding_census")
            .iter()
            .find(|entry| entry["language"] == language);
        let Some(found) = found else {
            errors.push(format!("no `{language}` binding_census entry"));
            continue;
        };
        for key in [
            "language",
            "candidates",
            "tagged",
            "bound",
            "self_named",
            "self_named_bound",
        ] {
            if let Some(value) = wanted.get(key) {
                if found.get(key) != Some(value) {
                    errors.push(format!(
                        "binding_census.{key} expected {value}, got {}",
                        found[key]
                    ));
                }
            }
        }
        for key in [
            "unbound_example",
            "unmatched_example",
            "self_named_unbound_example",
        ] {
            if let Some(value) = wanted.get(key) {
                let actual = found
                    .get(key)
                    .filter(|value| !value.is_null())
                    .map(|example| {
                        format!(
                            "{}:{}",
                            example["path"].as_str().unwrap_or(""),
                            example["line"]
                        )
                    });
                if actual.as_deref() != value.as_str() {
                    errors.push(format!(
                        "binding_census.{key} expected {value}, got {actual:?}"
                    ));
                }
            }
        }
    }
    for wanted in array(expect, "metrics") {
        let name = wanted["name"].as_str().unwrap_or("");
        let found = array(payload, "metrics")
            .iter()
            .find(|entry| entry["name"] == name);
        let Some(found) = found else {
            errors.push(format!("metric `{name}` absent"));
            continue;
        };
        for key in ["state", "value", "population", "examined", "matched"] {
            if let Some(value) = wanted.get(key) {
                if found.get(key) != Some(value) {
                    errors.push(format!("{name}.{key} expected {value}, got {}", found[key]));
                }
            }
        }
        if let Some(value) = wanted.get("hollow") {
            let positive = |key: &str| found[key].as_f64().is_some_and(|number| number > 0.0);
            let hollow = found["shape"] == "ratio"
                && positive("population")
                && positive("examined")
                && found["matched"].as_f64().unwrap_or(0.0) == 0.0;
            if value.as_bool() != Some(hollow) {
                errors.push(format!("{name}.hollow expected {value}, got {hollow}"));
            }
        }
    }
    let suspicions = array(payload, "suspicions");
    for wanted in array(expect, "suspicions") {
        let Some(kind) = wanted["kind"].as_str() else {
            errors.push("suspicions entries must be mappings with a kind".into());
            continue;
        };
        let found = suspicions.iter().find(|entry| entry["kind"] == kind);
        let Some(found) = found else {
            errors.push(format!("suspicion `{kind}` did not fire"));
            continue;
        };
        for field in ["path", "line", "symbol"] {
            if let Some(value) = wanted.get(field) {
                if found.get(field) != Some(value) {
                    errors.push(format!(
                        "suspicion `{kind}` {field} expected {value}, got {}",
                        found[field]
                    ));
                }
            }
        }
        for fragment in array(wanted, "message_contains")
            .iter()
            .filter_map(Value::as_str)
        {
            if !finding_text(found).contains(fragment) {
                errors.push(format!(
                    "suspicion `{kind}` finding text lacks {fragment:?}"
                ));
            }
        }
    }
    for kind in array(expect, "absent_suspicions")
        .iter()
        .filter_map(Value::as_str)
    {
        if suspicions.iter().any(|entry| entry["kind"] == kind) {
            errors.push(format!(
                "suspicion `{kind}` fired on input that must stay silent"
            ));
        }
    }
    errors
}

#[cfg(test)]
mod tests {
    use std::{collections::BTreeMap, fs, path::PathBuf};

    use serde_json::json;

    use super::{differential, grade, witness_channels};
    use crate::corpus::Case;

    /// Trace: FR-065-AC-5, FR-065-AC-28.
    #[test]
    fn absent_and_empty_exact_fields_are_distinct() {
        let payload = json!({"unbacked_rows": [{"document":"a", "row_id":"x", "target_ids":[]} ]});
        assert!(grade(&json!({}), &payload).is_empty());
        assert!(!grade(&json!({"unbacked_rows": []}), &payload).is_empty());
    }

    /// Trace: FR-065-AC-29.
    #[test]
    fn scalar_message_fragments_are_refused() {
        let payload = json!({"diagnostics": [{"reason":"example", "message":"anything"}]});
        assert!(!grade(
            &json!({"diagnostic_message_contains":{"example":"a"}}),
            &payload
        )
        .is_empty());
    }

    /// Trace: MP-202. A ratio over a nonempty unread population is hollow.
    #[test]
    fn hollow_metric_is_derived_from_shape_and_population() {
        let payload = json!({"metrics": [{"name":"recall", "shape":"ratio", "population":4,
            "examined":4, "matched":0}]});
        assert!(grade(
            &json!({"metrics":[{"name":"recall", "hollow":true}]}),
            &payload
        )
        .is_empty());
        assert!(!grade(
            &json!({"metrics":[{"name":"recall", "hollow":false}]}),
            &payload
        )
        .is_empty());
    }

    /// Trace: FR-065-AC-42, FR-065-AC-46. Incidental totals cannot witness disposition.
    #[test]
    fn differential_restricts_the_discriminating_channel() {
        let root = tempfile::tempdir().expect("scratch corpus");
        let directory = root.path().join("cases/disposition/failure");
        fs::create_dir_all(&directory).expect("case directory");
        let expect = PathBuf::from("cases/disposition/failure/expect.yaml");
        fs::write(root.path().join(&expect), "total: 1\n").expect("blind live block");
        let failure = Case {
            effective: json!({"id":"f", "kind":"failure", "mode":"disposition",
            "module":"ecosystem", "language":"rust"}),
            declared: json!({}),
            directory: PathBuf::from("cases/disposition/failure"),
            expectation: expect.clone(),
        };
        let control = Case {
            effective: json!({"id":"c", "kind":"control", "mode":"disposition",
            "module":"ecosystem", "language":"rust", "control_for":["f"]}),
            declared: json!({}),
            directory: PathBuf::from("cases/disposition/control"),
            expectation: PathBuf::from("cases/disposition/control/expect.yaml"),
        };
        let declaration = json!({"mode_families":["disposition"],
            "witness_channels":{"disposition":["unbacked_rows"]}});
        let payloads = BTreeMap::from([(
            ("c".into(), "rust".into()),
            json!({"totals":{"total":1}, "unbacked_rows":[]}),
        )]);
        let cases = [failure, control];
        let (_, failures) = differential(
            root.path(),
            &declaration,
            &cases,
            &payloads,
            &BTreeMap::new(),
            None,
        )
        .expect("grade pair");
        assert!(failures
            .iter()
            .any(|failure| failure.contains("expect.yaml holds against control")));
        assert!(failures
            .iter()
            .any(|failure| failure.contains("names no `disposition` witness channel")));
        fs::write(root.path().join(&expect), "total: 999\n").expect("incidental scalar");
        let (_, failures) = differential(
            root.path(),
            &declaration,
            &cases,
            &payloads,
            &BTreeMap::new(),
            None,
        )
        .expect("grade pair with incidental scalar");
        assert!(failures
            .iter()
            .any(|failure| failure.contains("names no `disposition` witness channel")));
        fs::write(
            root.path().join(&expect),
            "total: 999\nunbacked_rows:\n- document: a\n  row_id: x\n  target_ids: []\n",
        )
        .expect("mode witness");
        let (_, failures) = differential(
            root.path(),
            &declaration,
            &cases,
            &payloads,
            &BTreeMap::new(),
            None,
        )
        .expect("grade pair with witness");
        assert!(
            failures.is_empty(),
            "mode witness must discriminate: {failures:?}"
        );
    }

    /// Trace: FR-065-AC-47. A misspelled restriction cannot weaken the gate.
    #[test]
    fn unknown_witness_channel_is_rejected() {
        let declaration = json!({"mode_families":["disposition"],
            "witness_channels":{"disposition":["unbacked_rowz"]}});
        let error = witness_channels(&declaration).expect_err("unknown channel must fail");
        assert!(error.to_string().contains("cannot grade"));
    }
}
