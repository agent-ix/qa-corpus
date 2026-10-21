//! Strict corpus YAML admission and metadata validation (STD-227).

use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
};

use serde::{
    de::{MapAccess, SeqAccess, Visitor},
    Deserialize, Deserializer,
};
use serde_json::{Map, Number, Value};

/// Stable failure classes surfaced by corpus gates.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ErrorCode {
    /// A corpus input cannot be read.
    Input,
    /// A YAML document is malformed or has duplicate keys.
    Yaml,
    /// A case declaration violates the declared metadata schema.
    CaseMetadata,
}

impl ErrorCode {
    /// Stable code for machine-readable diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Input => "input",
            Self::Yaml => "yaml",
            Self::CaseMetadata => "case_metadata",
        }
    }

    /// All stable corpus error codes.
    pub const fn all() -> &'static [Self] {
        &[Self::Input, Self::Yaml, Self::CaseMetadata]
    }

    /// Decode one stable corpus error code.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "input" => Some(Self::Input),
            "yaml" => Some(Self::Yaml),
            "case_metadata" => Some(Self::CaseMetadata),
            _ => None,
        }
    }
}

/// One failed corpus gate operation.
#[derive(Debug, thiserror::Error)]
#[error("{code}: {message}", code = .code.as_str())]
pub struct CorpusError {
    /// Stable error class.
    pub code: ErrorCode,
    /// Human-readable diagnostic.
    pub message: Box<str>,
}

impl CorpusError {
    pub(crate) fn new(code: ErrorCode, message: impl Into<Box<str>>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }
}

/// One case after shared and per-language metadata have been merged.
#[derive(Clone, Debug)]
pub struct Case {
    /// Effective metadata with derived identity and location fields.
    pub effective: Value,
    /// Metadata as authored, before derived fields were inserted.
    pub declared: Value,
    /// Case input directory relative to the corpus root.
    pub directory: PathBuf,
    /// Expectation file relative to the corpus root.
    pub expectation: PathBuf,
}

fn directories(path: &Path) -> Result<Vec<PathBuf>, CorpusError> {
    let entries = fs::read_dir(path).map_err(|error| {
        CorpusError::new(ErrorCode::Input, format!("{}: {error}", path.display()))
    })?;
    let mut dirs = Vec::new();
    for entry in entries {
        let entry = entry.map_err(|error| CorpusError::new(ErrorCode::Input, error.to_string()))?;
        if entry
            .file_type()
            .map_err(|error| CorpusError::new(ErrorCode::Input, error.to_string()))?
            .is_dir()
        {
            dirs.push(entry.path());
        }
    }
    dirs.sort();
    Ok(dirs)
}

fn object(value: Value, path: &Path) -> Result<Map<String, Value>, CorpusError> {
    value.as_object().cloned().ok_or_else(|| {
        CorpusError::new(
            ErrorCode::Yaml,
            format!("{}: expected a mapping", path.display()),
        )
    })
}

/// Discover both single-language and language-set case layouts.
pub fn discover(root: &Path) -> Result<Vec<Case>, CorpusError> {
    let declaration = load_yaml(&root.join("corpus.yaml"))?;
    let schema = &declaration["case_schema"];
    let protected: Vec<_> = schema["variant_forbidden"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    if protected.is_empty() {
        return Err(CorpusError::new(
            ErrorCode::CaseMetadata,
            "corpus.yaml declares no `case_schema.variant_forbidden`",
        ));
    }
    let mut cases = Vec::new();
    for mode_dir in directories(&root.join("cases"))? {
        for case_dir in directories(&mode_dir)? {
            let shared_path = case_dir.join("case.yaml");
            let shared = object(load_yaml(&shared_path)?, &shared_path)?;
            let variants = directories(&case_dir)?
                .into_iter()
                .filter(|path| path.join("input").is_dir())
                .collect::<Vec<_>>();
            let relative = case_dir
                .strip_prefix(root)
                .map_err(|error| CorpusError::new(ErrorCode::Input, error.to_string()))?
                .to_path_buf();
            if case_dir.join("input").is_dir() {
                if !variants.is_empty() {
                    return Err(CorpusError::new(
                        ErrorCode::CaseMetadata,
                        format!(
                            "{}: carries both an `input/` and language variants",
                            relative.display()
                        ),
                    ));
                }
                let mut effective = shared.clone();
                effective.insert(
                    "dir".into(),
                    Value::String(relative.to_string_lossy().into_owned()),
                );
                effective.insert(
                    "expect".into(),
                    Value::String(relative.join("expect.yaml").to_string_lossy().into_owned()),
                );
                validate_case(
                    &Value::Object(shared.clone()),
                    schema,
                    &relative.to_string_lossy(),
                )?;
                cases.push(Case {
                    effective: Value::Object(effective),
                    declared: Value::Object(shared),
                    directory: relative.clone(),
                    expectation: relative.join("expect.yaml"),
                });
                continue;
            }
            if variants.is_empty() {
                return Err(CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!(
                        "{}: neither an `input/` nor any `<language>/input/`",
                        relative.display()
                    ),
                ));
            }
            for variant in variants {
                let language = variant
                    .file_name()
                    .and_then(|name| name.to_str())
                    .ok_or_else(|| {
                        CorpusError::new(ErrorCode::Input, "non-UTF-8 language directory")
                    })?;
                let variant_yaml = variant.join("case.yaml");
                let per_case = if variant_yaml.is_file() {
                    object(load_yaml(&variant_yaml)?, &variant_yaml)?
                } else {
                    Map::new()
                };
                for field in &protected {
                    if per_case.contains_key(*field) {
                        return Err(CorpusError::new(
                            ErrorCode::CaseMetadata,
                            format!(
                                "{}/{}: variant may not declare `{field}`",
                                relative.display(),
                                language
                            ),
                        ));
                    }
                }
                let mut declared = shared.clone();
                declared.extend(per_case);
                declared.insert("language".into(), Value::String(language.to_owned()));
                let mut effective = declared.clone();
                let base = effective
                    .get("id")
                    .and_then(Value::as_str)
                    .or_else(|| case_dir.file_name().and_then(|name| name.to_str()))
                    .ok_or_else(|| {
                        CorpusError::new(ErrorCode::CaseMetadata, "case has no identity")
                    })?
                    .to_owned();
                effective
                    .entry("case")
                    .or_insert_with(|| Value::String(base.clone()));
                effective.insert("id".into(), Value::String(format!("{base}-{language}")));
                let directory = variant
                    .strip_prefix(root)
                    .map_err(|error| CorpusError::new(ErrorCode::Input, error.to_string()))?
                    .to_path_buf();
                effective.insert(
                    "dir".into(),
                    Value::String(directory.to_string_lossy().into_owned()),
                );
                let expectation = directory.join("expect.yaml");
                effective.insert(
                    "expect".into(),
                    Value::String(expectation.to_string_lossy().into_owned()),
                );
                validate_case(
                    &Value::Object(declared.clone()),
                    schema,
                    &directory.to_string_lossy(),
                )?;
                cases.push(Case {
                    effective: Value::Object(effective),
                    declared: Value::Object(declared),
                    directory,
                    expectation,
                });
            }
        }
    }
    for field in schema["unique"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
    {
        let mut seen = BTreeMap::new();
        for case in &cases {
            let Some(value) = case.effective.get(field) else {
                continue;
            };
            let identity = value.to_string();
            if let Some(previous) =
                seen.insert(identity.clone(), case.directory.display().to_string())
            {
                return Err(CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!(
                        "{}: `{field}` {identity} is already used by {previous}",
                        case.directory.display()
                    ),
                ));
            }
        }
    }
    check_grading_contracts(&declaration, &cases)?;
    check_known_gaps(&declaration, &cases)?;
    let detection: Vec<_> = cases
        .iter()
        .filter(|case| case.effective["mode"] != "reporting")
        .cloned()
        .collect();
    check_controls(&declaration, &detection)?;
    check_expectation_shapes(root, &declaration, &detection)?;
    check_published_counts(root, &cases, &detection)?;
    Ok(cases)
}

fn check_published_counts(
    root: &Path,
    cases: &[Case],
    detection: &[Case],
) -> Result<(), CorpusError> {
    let failures: Vec<_> = detection
        .iter()
        .filter(|case| case.effective["kind"] == "failure")
        .collect();
    let controlled = controls_by_case(detection);
    let counts = BTreeMap::from([
        ("fixtures", cases.len()),
        ("failure_fixtures", failures.len()),
        (
            "controlled_failures",
            failures
                .iter()
                .filter(|case| {
                    let id = case.effective["id"].as_str().unwrap_or("");
                    let language = case.effective["language"].as_str().unwrap_or("");
                    controlled.contains_key(&(id.to_owned(), language.to_owned()))
                })
                .count(),
        ),
        ("pairs", controlled.values().map(Vec::len).sum()),
    ]);
    for relative in ["corpus.yaml", "README.md"] {
        let path = root.join(relative);
        if !path.is_file() {
            continue;
        }
        let source = fs::read_to_string(&path).map_err(|error| {
            CorpusError::new(ErrorCode::Input, format!("{}: {error}", path.display()))
        })?;
        for (line, content) in source.lines().enumerate() {
            for segment in content.split("<derived:").skip(1) {
                let Some((marker, _)) = segment.split_once('>') else {
                    continue;
                };
                let Some((name, written)) = marker.split_once('=') else {
                    continue;
                };
                let Some(expected) = counts.get(name) else {
                    return Err(CorpusError::new(
                        ErrorCode::CaseMetadata,
                        format!("{relative}:{}: `{name}` is not a derived count", line + 1),
                    ));
                };
                if written.parse::<usize>().ok() != Some(*expected) {
                    return Err(CorpusError::new(
                        ErrorCode::CaseMetadata,
                        format!(
                            "{relative}:{}: publishes {name}={written}, tree has {expected}",
                            line + 1
                        ),
                    ));
                }
            }
        }
    }
    Ok(())
}

const EXACT_FIELDS: &[&str] = &[
    "backed",
    "total",
    "unbacked_rows",
    "groups",
    "no_symbol_rows",
    "untracked_symbols",
    "external_observations",
];
const EXPECT_FIELDS: &[&str] = &[
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

fn asserts_something(block: &Value) -> bool {
    EXPECT_FIELDS.iter().any(|key| {
        let Some(value) = block.get(*key) else {
            return false;
        };
        if value.is_null() {
            return false;
        }
        if EXACT_FIELDS.contains(key) {
            return true;
        }
        match value {
            Value::Array(items) => !items.is_empty(),
            Value::Object(items) => !items.is_empty(),
            Value::String(text) => !text.is_empty(),
            _ => true,
        }
    })
}

fn check_block(name: &str, block: &Value, filename: &str) -> Result<(), CorpusError> {
    let fields = block.as_object().ok_or_else(|| {
        CorpusError::new(
            ErrorCode::CaseMetadata,
            format!("{name}: {filename} must be a mapping"),
        )
    })?;
    for key in fields.keys() {
        if !EXPECT_FIELDS.contains(&key.as_str()) {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("{name}: {filename} declares unhandled key `{key}`"),
            ));
        }
    }
    if !asserts_something(block) {
        return Err(CorpusError::new(
            ErrorCode::CaseMetadata,
            format!("{name}: {filename} asserts nothing"),
        ));
    }
    Ok(())
}

fn reason_names(block: &Value, fields: &[&str]) -> Vec<String> {
    let mut reasons = Vec::new();
    for field in fields {
        if let Some(items) = block[*field].as_array() {
            reasons.extend(items.iter().filter_map(Value::as_str).map(str::to_owned));
        }
        if let Some(items) = block[*field].as_object() {
            reasons.extend(items.keys().cloned());
        }
    }
    reasons
}

fn reason_token(reason: &str) -> &str {
    reason.rsplit('/').next().unwrap_or(reason)
}

fn check_reasons(
    id: &str,
    block: &Value,
    filename: &str,
    kind: &str,
    ticket: Option<&str>,
    emitted: &std::collections::BTreeSet<String>,
    forward: &BTreeMap<String, String>,
) -> Result<(Vec<String>, Vec<String>), CorpusError> {
    let present = reason_names(
        block,
        &[
            "diagnostic_reasons",
            "diagnostic_paths",
            "diagnostic_lines",
            "diagnostic_message_contains",
        ],
    );
    let absent = reason_names(block, &["absent_diagnostic_reasons"]);
    for reason in present.iter().chain(&absent) {
        let name = reason_token(reason);
        if !emitted.contains(name) && !forward.contains_key(name) {
            return Err(CorpusError::new(ErrorCode::CaseMetadata,
                format!("{id}: {filename} names `{name}`, which corpus.yaml declares neither emitted nor forward")));
        }
    }
    for reason in &present {
        let name = reason_token(reason);
        if let Some(owner) = forward.get(name) {
            if filename != "expect-pending.yaml" {
                return Err(CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!(
                        "{id}: {filename} requires `{name}`, which no engine emits yet ({owner})"
                    ),
                ));
            }
            if ticket != Some(owner.as_str()) {
                return Err(CorpusError::new(ErrorCode::CaseMetadata,
                    format!("{id}: pending ticket {ticket:?} asserts `{name}`, which {owner} introduces")));
            }
        } else if filename == "expect-pending.yaml" {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!(
                    "{id}: expect-pending.yaml requires `{name}`, which the engine already emits"
                ),
            ));
        }
    }
    for reason in &absent {
        let name = reason_token(reason);
        if forward.contains_key(name) && (kind != "control" || filename != "expect.yaml") {
            return Err(CorpusError::new(ErrorCode::CaseMetadata,
                format!("{id}: {filename} asserts forward token `{name}` is absent outside a live control")));
        }
    }
    Ok((
        present
            .into_iter()
            .map(|reason| reason_token(&reason).to_owned())
            .collect(),
        absent
            .into_iter()
            .map(|reason| reason_token(&reason).to_owned())
            .collect(),
    ))
}

fn check_expectation_shapes(
    root: &Path,
    declaration: &Value,
    cases: &[Case],
) -> Result<(), CorpusError> {
    let behaviour_change: std::collections::BTreeSet<_> = declaration["behaviour_change_tickets"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    let controlled = controls_by_case(cases);
    let undetected: std::collections::BTreeSet<_> = declaration["known_gaps"]
        ["findable_but_undetected"]["cases"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    let emitted: std::collections::BTreeSet<String> = declaration["diagnostic_reasons"]["emitted"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .map(str::to_owned)
        .collect();
    let mut forward = BTreeMap::new();
    for field in ["forward", "suppressed"] {
        if let Some(items) = declaration["diagnostic_reasons"][field].as_object() {
            for (name, owner) in items {
                if let Some(owner) = owner.as_str() {
                    forward.insert(name.clone(), owner.to_owned());
                }
            }
        }
    }
    let mut asserted_present = std::collections::BTreeSet::new();
    let mut asserted_absent = std::collections::BTreeSet::new();
    for case in cases {
        let meta = &case.effective;
        let id = meta["id"].as_str().unwrap_or("unknown case");
        let language = meta["language"].as_str().unwrap_or("");
        let ticket = meta["pending"].as_str();
        let forward_path = root.join(&case.directory).join("expect-pending.yaml");
        let has_forward = forward_path.is_file();
        if ticket.is_some() != has_forward {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("{id}: `pending:` and expect-pending.yaml must occur together"),
            ));
        }
        if ticket.is_some()
            && !meta["pending_reason"]
                .as_str()
                .is_some_and(|reason| !reason.trim().is_empty())
        {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("{id}: pending case has no `pending_reason`"),
            ));
        }
        if meta["kind"] == "control" && case.declared.get("case").is_some() {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("{id}: a control declares `case:`"),
            ));
        }
        if meta["kind"] == "regression"
            && (meta["findable"] == true || !meta["control_for"].is_null() || ticket.is_some())
        {
            return Err(CorpusError::new(ErrorCode::CaseMetadata,
                format!("{id}: a regression case pins landed behavior and cannot be findable, controlled, or pending")));
        }
        let live = load_yaml(&root.join(&case.expectation))?;
        check_block(id, &live, "expect.yaml")?;
        let (present, absent) = check_reasons(
            id,
            &live,
            "expect.yaml",
            meta["kind"].as_str().unwrap_or(""),
            ticket,
            &emitted,
            &forward,
        )?;
        asserted_present.extend(present);
        asserted_absent.extend(absent);
        let ahead = if has_forward {
            let block = load_yaml(&forward_path)?;
            check_block(id, &block, "expect-pending.yaml")?;
            check_reasons(
                id,
                &block,
                "expect-pending.yaml",
                meta["kind"].as_str().unwrap_or(""),
                ticket,
                &emitted,
                &forward,
            )?;
            Some(block)
        } else {
            None
        };
        if let (Some(ticket), Some(ahead)) = (ticket, ahead.as_ref()) {
            if behaviour_change.contains(ticket) {
                let graded: Vec<_> = EXACT_FIELDS
                    .iter()
                    .filter(|key| live.get(**key).is_some_and(|v| !v.is_null()))
                    .collect();
                if graded.is_empty()
                    || graded
                        .iter()
                        .any(|key| ahead.get(**key).is_none_or(Value::is_null))
                {
                    return Err(CorpusError::new(ErrorCode::CaseMetadata,
                        format!("{id}: behavior-change forward block must restate every exactly graded key")));
                }
                if graded.iter().all(|key| ahead.get(**key) == live.get(**key)) {
                    return Err(CorpusError::new(
                        ErrorCode::CaseMetadata,
                        format!("{id}: expect-pending.yaml asserts exactly what expect.yaml does"),
                    ));
                }
            } else {
                let claims = reason_names(
                    ahead,
                    &[
                        "diagnostic_reasons",
                        "diagnostic_paths",
                        "diagnostic_lines",
                        "diagnostic_message_contains",
                    ],
                );
                if !claims.iter().any(|reason| {
                    forward
                        .get(reason_token(reason))
                        .is_some_and(|owner| owner == ticket)
                }) {
                    return Err(CorpusError::new(
                        ErrorCode::CaseMetadata,
                        format!(
                            "{id}: expect-pending.yaml requires no token that {ticket} introduces"
                        ),
                    ));
                }
            }
        }
        if meta["kind"] == "failure"
            && meta["findable"] == true
            && !controlled.contains_key(&(id.to_owned(), language.to_owned()))
        {
            let names_finding = [
                "diagnostic_reasons",
                "validate_contains",
                "suspicions",
                "external_observations",
            ]
            .iter()
            .any(|key| {
                [Some(&live), ahead.as_ref()]
                    .into_iter()
                    .flatten()
                    .any(|block| {
                        block.get(*key).is_some_and(|value| {
                            !value.is_null() && value != &Value::Array(Vec::new())
                        })
                    })
            });
            let row = meta["case"].as_str().unwrap_or(id);
            if !names_finding && !undetected.contains(row) && !undetected.contains(id) {
                return Err(CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!("{id}: is `findable` and requires no finding"),
                ));
            }
        }
    }
    let missing_positive: Vec<_> = emitted.difference(&asserted_present).cloned().collect();
    let missing_negative: Vec<_> = emitted.difference(&asserted_absent).cloned().collect();
    if !missing_positive.is_empty() || !missing_negative.is_empty() {
        return Err(CorpusError::new(ErrorCode::CaseMetadata,
            format!("diagnostic reason coverage is incomplete: asserted present missing {missing_positive:?}; asserted absent missing {missing_negative:?}")));
    }
    Ok(())
}

/// Resolve a control's named partner by failure id first, then row alias.
pub fn failure_partners(cases: &[Case]) -> BTreeMap<(String, String), &Case> {
    let mut partners = BTreeMap::new();
    for case in cases {
        let meta = &case.effective;
        if meta["kind"] != "failure" {
            continue;
        }
        if let (Some(alias), Some(language)) = (meta["case"].as_str(), meta["language"].as_str()) {
            partners
                .entry((alias.to_owned(), language.to_owned()))
                .or_insert(case);
        }
    }
    for case in cases {
        let meta = &case.effective;
        if meta["kind"] != "failure" {
            continue;
        }
        if let (Some(id), Some(language)) = (meta["id"].as_str(), meta["language"].as_str()) {
            partners.insert((id.to_owned(), language.to_owned()), case);
        }
    }
    partners
}

/// All healthy controls for each failure, preserving multiple valid partners.
pub fn controls_by_case(cases: &[Case]) -> BTreeMap<(String, String), Vec<&Case>> {
    let partners = failure_partners(cases);
    let mut controlled: BTreeMap<(String, String), Vec<&Case>> = BTreeMap::new();
    for control in cases {
        let meta = &control.effective;
        if meta["kind"] != "control" {
            continue;
        }
        let Some(language) = meta["language"].as_str() else {
            continue;
        };
        for name in meta["control_for"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
        {
            if let Some(failure) = partners.get(&(name.to_owned(), language.to_owned())) {
                let id = failure.effective["id"].as_str().unwrap_or("");
                controlled
                    .entry((id.to_owned(), language.to_owned()))
                    .or_default()
                    .push(control);
            }
        }
    }
    controlled
}

fn check_controls(declaration: &Value, cases: &[Case]) -> Result<(), CorpusError> {
    let partners = failure_partners(cases);
    let controlled = controls_by_case(cases);
    let gap_cases = |name: &str| -> std::collections::BTreeSet<&str> {
        declaration["known_gaps"][name]["cases"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .collect()
    };
    let module_gaps = gap_cases("control_binds_another_module");
    let uncontrolled = gap_cases("uncontrolled_failure_cases");
    for case in cases {
        let meta = &case.effective;
        let Some(id) = meta["id"].as_str() else {
            continue;
        };
        let language = meta["language"].as_str().unwrap_or("");
        if meta["kind"] == "control" {
            let names = meta["control_for"]
                .as_array()
                .filter(|names| !names.is_empty())
                .ok_or_else(|| {
                    CorpusError::new(
                        ErrorCode::CaseMetadata,
                        format!("{id}: a control declares no `control_for`"),
                    )
                })?;
            for name in names {
                let name = name.as_str().ok_or_else(|| {
                    CorpusError::new(
                        ErrorCode::CaseMetadata,
                        format!("{id}: `control_for` must list strings"),
                    )
                })?;
                let failure = partners.get(&(name.to_owned(), language.to_owned())).ok_or_else(|| {
                    CorpusError::new(ErrorCode::CaseMetadata,
                        format!("{id}: control_for names `{name}`, which is no failure case in {language}"))
                })?;
                for field in ["mode", "module"] {
                    if meta[field] != failure.effective[field]
                        && !(field == "module" && module_gaps.contains(id))
                    {
                        return Err(CorpusError::new(ErrorCode::CaseMetadata,
                            format!("{id}: control_for names `{name}`, whose {field} differs from this control")));
                    }
                }
            }
            if meta["findable"] == true {
                return Err(CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!("{id}: a control cannot be findable"),
                ));
            }
        } else if meta["kind"] == "failure" {
            let row = meta["case"].as_str().unwrap_or(id);
            if !controlled.contains_key(&(id.to_owned(), language.to_owned()))
                && !uncontrolled.contains(row)
                && !uncontrolled.contains(id)
            {
                return Err(CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!("{id}: no control names it (FR-065-AC-13)"),
                ));
            }
        }
    }
    Ok(())
}

fn check_grading_contracts(declaration: &Value, cases: &[Case]) -> Result<(), CorpusError> {
    let levels = declaration["grading_levels"].as_array().ok_or_else(|| {
        CorpusError::new(
            ErrorCode::CaseMetadata,
            "corpus.yaml: grading_levels must be a list",
        )
    })?;
    if levels.is_empty() {
        return Err(CorpusError::new(
            ErrorCode::CaseMetadata,
            "corpus.yaml: grading_levels is empty",
        ));
    }
    for case in cases {
        let meta = &case.effective;
        if meta["kind"] != "failure" || meta["findable"] != true || meta["mode"] == "reporting" {
            continue;
        }
        let id = meta["id"].as_str().unwrap_or("unknown case");
        let contract = meta["grading_contract"].as_object().ok_or_else(|| {
            CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("{id}: a findable failure must declare `grading_contract`"),
            )
        })?;
        for key in contract.keys() {
            if key != "channel" && key != "levels" {
                return Err(CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!("{id}: grading_contract has unknown key `{key}`"),
                ));
            }
        }
        let channel = contract
            .get("channel")
            .and_then(Value::as_str)
            .unwrap_or("");
        if !["finding", "direct-observation", "behavior"].contains(&channel) {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("{id}: grading_contract.channel `{channel}` is not declared"),
            ));
        }
        let declared = contract
            .get("levels")
            .and_then(Value::as_object)
            .ok_or_else(|| {
                CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!("{id}: grading_contract.levels must be a mapping"),
                )
            })?;
        if declared.len() != levels.len() {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("{id}: grading_contract.levels must declare every grading level"),
            ));
        }
        for level in levels {
            let name = level.as_str().ok_or_else(|| {
                CorpusError::new(
                    ErrorCode::CaseMetadata,
                    "corpus.yaml: grading_levels contains a non-string",
                )
            })?;
            let entry = declared
                .get(name)
                .and_then(Value::as_object)
                .ok_or_else(|| {
                    CorpusError::new(
                        ErrorCode::CaseMetadata,
                        format!("{id}: grading_contract.levels.{name} must be a mapping"),
                    )
                })?;
            if entry.keys().any(|key| key != "state" && key != "reason") {
                return Err(CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!("{id}: grading_contract.levels.{name} has unknown keys"),
                ));
            }
            let state = entry.get("state").and_then(Value::as_str).unwrap_or("");
            if !["required", "not_applicable"].contains(&state) {
                return Err(CorpusError::new(ErrorCode::CaseMetadata,
                    format!("{id}: grading_contract.levels.{name}.state `{state}` is not one of required, not_applicable")));
            }
            if state == "not_applicable"
                && !entry
                    .get("reason")
                    .and_then(Value::as_str)
                    .is_some_and(|s| !s.trim().is_empty())
            {
                return Err(CorpusError::new(ErrorCode::CaseMetadata,
                    format!("{id}: grading_contract.levels.{name} excludes the case without a non-empty reason")));
            }
            if state == "required" && entry.contains_key("reason") {
                return Err(CorpusError::new(ErrorCode::CaseMetadata,
                    format!("{id}: grading_contract.levels.{name} is required and may not carry an exclusion reason")));
            }
        }
        let states = |name: &str| {
            declared
                .get(name)
                .and_then(|value| value.get("state"))
                .and_then(Value::as_str)
        };
        if channel == "behavior"
            && levels
                .iter()
                .filter_map(Value::as_str)
                .any(|name| states(name) != Some("not_applicable"))
        {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("{id}: a behavior case must exclude all finding levels"),
            ));
        }
        if channel == "direct-observation"
            && (states("L1") != Some("required")
                || states("L2") != Some("required")
                || states("L3") != Some("not_applicable"))
        {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("{id}: a direct observation requires L1/L2 and excludes finding-level L3"),
            ));
        }
        if channel == "finding" && states("L1") != Some("required") {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("{id}: a finding channel must require L1"),
            ));
        }
    }
    Ok(())
}

fn check_known_gaps(declaration: &Value, cases: &[Case]) -> Result<(), CorpusError> {
    let Some(gaps) = declaration["known_gaps"].as_object() else {
        return Ok(());
    };
    let mut names = std::collections::BTreeSet::new();
    for case in cases {
        let meta = &case.effective;
        if let Some(id) = meta["id"].as_str() {
            names.insert(id);
        }
        if let Some(row) = meta["case"].as_str() {
            names.insert(row);
        }
    }
    for (name, gap) in gaps {
        let reason = gap["reason"].as_str().unwrap_or("");
        let ticket = reason.find('#').is_some_and(|index| {
            reason[index + 1..]
                .chars()
                .next()
                .is_some_and(|ch| ch.is_ascii_digit())
        });
        if !ticket {
            return Err(CorpusError::new(
                ErrorCode::CaseMetadata,
                format!("known_gaps.{name}: its reason names no ticket"),
            ));
        }
        let listed = gap["cases"]
            .as_array()
            .filter(|items| !items.is_empty())
            .ok_or_else(|| {
                CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!("known_gaps.{name}: declares no cases"),
                )
            })?;
        for item in listed {
            let case = item.as_str().ok_or_else(|| {
                CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!("known_gaps.{name}: case name is not a string"),
                )
            })?;
            if !names.contains(case) {
                return Err(CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!("known_gaps.{name} names `{case}`, which is no case in the corpus"),
                ));
            }
        }
    }
    let waited_on: std::collections::BTreeSet<_> = cases
        .iter()
        .filter_map(|case| case.effective["pending"].as_str())
        .collect();
    for ticket in declaration["behaviour_change_tickets"]
        .as_array()
        .into_iter()
        .flatten()
    {
        if let Some(ticket) = ticket.as_str() {
            if !waited_on.contains(ticket) {
                return Err(CorpusError::new(
                    ErrorCode::CaseMetadata,
                    format!(
                        "behaviour_change_tickets names `{ticket}`, which no case is pending on"
                    ),
                ));
            }
        }
    }
    Ok(())
}

/// Parse one YAML file, refusing duplicate mapping keys at every nesting level.
pub fn load_yaml(path: &Path) -> Result<Value, CorpusError> {
    let source = fs::read_to_string(path).map_err(|error| {
        CorpusError::new(ErrorCode::Input, format!("{}: {error}", path.display()))
    })?;
    serde_yaml::from_str::<StrictValue>(&source)
        .map(|value| value.0)
        .map_err(|error| CorpusError::new(ErrorCode::Yaml, format!("{}: {error}", path.display())))
}

#[derive(Debug)]
struct StrictValue(Value);

impl<'de> Deserialize<'de> for StrictValue {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(StrictVisitor)
    }
}

struct StrictVisitor;

impl<'de> Visitor<'de> for StrictVisitor {
    type Value = StrictValue;

    fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("a JSON-compatible YAML value without duplicate keys")
    }

    fn visit_bool<E: serde::de::Error>(self, value: bool) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Bool(value)))
    }

    fn visit_i64<E: serde::de::Error>(self, value: i64) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Number(Number::from(value))))
    }

    fn visit_u64<E: serde::de::Error>(self, value: u64) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Number(Number::from(value))))
    }

    fn visit_f64<E: serde::de::Error>(self, value: f64) -> Result<Self::Value, E> {
        Number::from_f64(value)
            .map(Value::Number)
            .map(StrictValue)
            .ok_or_else(|| E::custom("non-finite number"))
    }

    fn visit_str<E: serde::de::Error>(self, value: &str) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::String(value.to_owned())))
    }

    fn visit_string<E: serde::de::Error>(self, value: String) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::String(value)))
    }

    fn visit_none<E: serde::de::Error>(self) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Null))
    }

    fn visit_unit<E: serde::de::Error>(self) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Null))
    }

    fn visit_some<D: Deserializer<'de>>(self, deserializer: D) -> Result<Self::Value, D::Error> {
        StrictValue::deserialize(deserializer)
    }

    fn visit_seq<A: SeqAccess<'de>>(self, mut access: A) -> Result<Self::Value, A::Error> {
        let mut values = Vec::new();
        while let Some(value) = access.next_element::<StrictValue>()? {
            values.push(value.0);
        }
        Ok(StrictValue(Value::Array(values)))
    }

    fn visit_map<A: MapAccess<'de>>(self, mut access: A) -> Result<Self::Value, A::Error> {
        let mut values = Map::new();
        while let Some((key, value)) = access.next_entry::<String, StrictValue>()? {
            if values.contains_key(&key) {
                return Err(serde::de::Error::custom(format!("duplicate key {key:?}")));
            }
            values.insert(key, value.0);
        }
        Ok(StrictValue(Value::Object(values)))
    }
}

/// Validate one effective case record against `corpus.yaml`'s `case_schema`.
pub fn validate_case(case: &Value, schema: &Value, where_: &str) -> Result<(), CorpusError> {
    let mut problems = Vec::new();
    let kind = case["kind"].as_str().unwrap_or("");
    let by_kind = &schema["by_kind"][kind];
    if by_kind.is_null() {
        problems.push(format!(
            "{where_}: kind `{kind}` has no `case_schema.by_kind` entry"
        ));
    }
    let fields = schema["required"]
        .as_array()
        .into_iter()
        .flatten()
        .chain(by_kind["required"].as_array().into_iter().flatten());
    for field in fields {
        let Some(name) = field.as_str() else { continue };
        match case.get(name) {
            None => problems.push(format!("{where_}: required field `{name}` is missing")),
            Some(Value::Null) | Some(Value::String(_))
                if case[name].as_str().is_none_or(str::is_empty) =>
            {
                problems.push(format!("{where_}: `{name}` is present but empty"))
            }
            Some(Value::Array(items)) if items.is_empty() => {
                problems.push(format!("{where_}: `{name}` is present but empty"))
            }
            Some(Value::Object(items)) if items.is_empty() => {
                problems.push(format!("{where_}: `{name}` is present but empty"))
            }
            _ => {}
        }
    }
    for field in by_kind["forbidden"].as_array().into_iter().flatten() {
        if let Some(name) = field.as_str() {
            if case.get(name).is_some() {
                problems.push(format!(
                    "{where_}: a `{kind}` case may not declare `{name}`"
                ));
            }
        }
    }
    for (name, allowed) in by_kind["values"]
        .as_object()
        .into_iter()
        .flat_map(|map| map.iter())
    {
        if let Some(value) = case.get(name) {
            if !allowed
                .as_array()
                .is_some_and(|items| items.contains(value))
            {
                problems.push(format!(
                    "{where_}: `{name}: {value}` is not an allowed `{kind}` value"
                ));
            }
        }
    }
    for (name, specification) in schema["types"]
        .as_object()
        .into_iter()
        .flat_map(|map| map.iter())
    {
        let Some(value) = case.get(name) else {
            continue;
        };
        let (valid, wanted) = match specification {
            Value::String(kind) if kind == "str" => (value.is_string(), "a string"),
            Value::String(kind) if kind == "bool" => (value.is_boolean(), "true or false"),
            Value::String(kind) if kind == "grading_contract" => {
                (value.is_object(), "a grading contract mapping")
            }
            Value::Array(kinds) if kinds == &[Value::String("str".into())] => (
                value
                    .as_array()
                    .is_some_and(|items| items.iter().all(Value::is_string)),
                "a list of strings",
            ),
            _ => {
                problems.push(format!(
                    "corpus.yaml: `case_schema.types` declares unknown type for `{name}`"
                ));
                continue;
            }
        };
        if !valid {
            problems.push(format!("{where_}: `{name}` must be {wanted}, got {value}"));
        }
    }
    if let Some(fields) = case.as_object() {
        let known: std::collections::BTreeSet<_> = schema["required"]
            .as_array()
            .into_iter()
            .flatten()
            .chain(schema["optional"].as_array().into_iter().flatten())
            .filter_map(Value::as_str)
            .chain(std::iter::once("language"))
            .collect();
        for name in fields.keys() {
            if !known.contains(name.as_str()) {
                problems.push(format!(
                    "{where_}: `{name}` is in neither `required` nor `optional`"
                ));
            }
        }
    }
    for (index, rule) in schema["conditional"]
        .as_array()
        .into_iter()
        .flatten()
        .enumerate()
    {
        let Some(rule) = rule.as_object() else {
            problems.push(format!(
                "corpus.yaml: case_schema.conditional[{index}] must be a mapping"
            ));
            continue;
        };
        let fires = if let Some(trigger) = rule.get("if_present").and_then(Value::as_str) {
            case.get(trigger).is_some()
        } else if let Some(condition) = rule.get("if_field_is_not") {
            let Some(condition) = condition.as_object() else {
                problems.push(format!("corpus.yaml: case_schema.conditional[{index}].if_field_is_not must be a one-entry mapping"));
                continue;
            };
            if condition.len() != 1 {
                problems.push(format!("corpus.yaml: case_schema.conditional[{index}].if_field_is_not must be a one-entry mapping"));
                continue;
            }
            let (field, value) = condition.iter().next().ok_or_else(|| {
                CorpusError::new(ErrorCode::CaseMetadata, "empty conditional mapping")
            })?;
            case.get(field) != Some(value)
        } else {
            problems.push(format!(
                "corpus.yaml: case_schema.conditional[{index}] has no trigger"
            ));
            continue;
        };
        if fires {
            for field in rule
                .get("then_required")
                .and_then(Value::as_array)
                .into_iter()
                .flatten()
            {
                if let Some(name) = field.as_str() {
                    if case.get(name).is_none() {
                        let because = rule
                            .get("why")
                            .and_then(Value::as_str)
                            .unwrap_or("declared in `case_schema`");
                        problems.push(format!("{where_}: `{name}` is required here — {because}"));
                    }
                }
            }
        }
    }
    if problems.is_empty() {
        Ok(())
    } else {
        Err(CorpusError::new(
            ErrorCode::CaseMetadata,
            problems.join("\n"),
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::{controls_by_case, discover, failure_partners, validate_case, StrictValue};
    use serde_json::json;
    use std::fs;

    /// Trace: FR-065-AC-1
    #[test]
    fn nested_duplicate_yaml_key_is_rejected() {
        let duplicate =
            "expect:\n  diagnostic_message_contains:\n    reason: one\n    reason: two\n";
        let error = serde_yaml::from_str::<StrictValue>(duplicate).unwrap_err();
        assert!(error.to_string().contains("duplicate key \"reason\""));
    }

    /// Trace: FR-065-AC-1
    #[test]
    fn required_case_field_must_be_written_and_nonempty() {
        let schema = json!({"required": ["id", "issue_ref"], "by_kind": {"failure": {}}});
        let missing = json!({"kind": "failure", "id": "case"});
        assert!(validate_case(&missing, &schema, "case.yaml")
            .unwrap_err()
            .to_string()
            .contains("required field `issue_ref` is missing"));
        let empty = json!({"kind": "failure", "id": "case", "issue_ref": ""});
        assert!(validate_case(&empty, &schema, "case.yaml")
            .unwrap_err()
            .to_string()
            .contains("`issue_ref` is present but empty"));
    }

    /// Trace: FR-065-AC-1. Conditional rules follow the declaration and reject malformed rules.
    #[test]
    fn conditional_schema_rule_fires_and_rejects_bad_shape() {
        let mut schema = json!({
            "required": ["kind"], "optional": ["ticket"],
            "by_kind": {"failure": {}, "control": {}},
            "conditional": [{"if_field_is_not": {"kind": "control"}, "then_required": ["ticket"]}]
        });
        assert!(validate_case(&json!({"kind": "control"}), &schema, "control").is_ok());
        let missing = validate_case(&json!({"kind": "failure"}), &schema, "failure")
            .expect_err("failure requires ticket");
        assert!(missing.to_string().contains("`ticket` is required here"));
        schema["conditional"][0]["if_field_is_not"] = json!(["kind", "control"]);
        let malformed = validate_case(&json!({"kind": "failure"}), &schema, "failure")
            .expect_err("malformed conditional cannot be ignored");
        assert!(malformed
            .to_string()
            .contains("must be a one-entry mapping"));
    }

    /// Trace: FR-065-AC-22
    #[test]
    fn variant_cannot_repoint_the_shared_case_identity() {
        let root = tempfile::tempdir().unwrap();
        fs::write(root.path().join("corpus.yaml"),
            "case_schema:\n  required: [id, kind, mode, language]\n  optional: [case]\n  by_kind:\n    failure: {}\n  variant_forbidden: [id, mode]\n  unique: [id]\n").unwrap();
        let case = root.path().join("cases/detection/pair");
        fs::create_dir_all(case.join("rust/input")).unwrap();
        fs::write(
            case.join("case.yaml"),
            "id: pair\nkind: failure\nmode: detection\n",
        )
        .unwrap();
        fs::write(case.join("rust/case.yaml"), "id: repointed\n").unwrap();
        let error = discover(root.path()).unwrap_err();
        assert!(error.to_string().contains("variant may not declare `id`"));
    }

    /// Trace: FR-065-AC-13, FR-065-AC-42. Every control remains paired.
    #[test]
    fn controls_keep_every_partner_of_one_failure() {
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
        let cases = discover(root).expect("checked-in corpus loads");
        let detection: Vec<_> = cases
            .into_iter()
            .filter(|case| case.effective["mode"] != "reporting")
            .collect();
        let partners = failure_partners(&detection);
        let exact = partners
            .get(&("marker-form-mismatch-rust".into(), "rust".into()))
            .expect("exact failure id resolves");
        assert_eq!(exact.effective["id"], "marker-form-mismatch-rust");
        let controlled = controls_by_case(&detection);
        let controls = controlled
            .get(&("marker-form-mismatch-rust".into(), "rust".into()))
            .expect("the failure has controls");
        assert!(
            controls.len() >= 2,
            "all controls of one failure must be retained"
        );
    }
}
