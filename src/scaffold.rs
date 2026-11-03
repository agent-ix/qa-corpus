//! Authoring scaffold for a new controlled corpus case.

use std::{
    fs,
    path::{Component, Path, PathBuf},
};

use serde_json::{json, Value};

use crate::corpus::{load_yaml, CorpusError, ErrorCode};

fn invalid(message: impl Into<Box<str>>) -> CorpusError {
    CorpusError::new(ErrorCode::CaseMetadata, message)
}

/// Inputs to the authoring scaffold.
pub struct Options<'a> {
    /// Declared mode family.
    pub mode: &'a str,
    /// Inventory case name.
    pub case: &'a str,
    /// Source language.
    pub language: &'a str,
    /// Failure, control or regression.
    pub kind: &'a str,
    /// Module path beneath `modules/`.
    pub module: &'a str,
    /// Source filing for this fixture.
    pub issue: &'a str,
}

fn module_selector(root: &Path, module: &str) -> Result<String, CorpusError> {
    if module.is_empty()
        || !Path::new(module)
            .components()
            .all(|part| matches!(part, Component::Normal(_)))
    {
        return Err(invalid("module must be a relative path beneath modules/"));
    }
    let base = root.join("modules").join(module);
    if base.join("manifest.yaml").is_file() {
        return Ok(format!("--module modules/{module}"));
    }
    if base.is_dir() {
        let entries = fs::read_dir(&base).map_err(|error| {
            CorpusError::new(ErrorCode::Input, format!("{}: {error}", base.display()))
        })?;
        for entry in entries {
            let entry =
                entry.map_err(|error| CorpusError::new(ErrorCode::Input, error.to_string()))?;
            if entry.path().join("manifest.yaml").is_file() {
                return Ok(format!("IX_FILAMENT_MODULES_PATH=modules/{module}"));
            }
        }
    }
    Err(invalid(format!(
        "module `{module}` names neither a manifest nor a directory of them under modules/"
    )))
}

fn write(path: &Path, contents: &str) -> Result<(), CorpusError> {
    fs::write(path, contents)
        .map_err(|error| CorpusError::new(ErrorCode::Input, format!("{}: {error}", path.display())))
}

fn yaml_write(path: &Path, value: &Value) -> Result<(), CorpusError> {
    let contents = serde_yaml::to_string(value)
        .map_err(|error| invalid(format!("{}: {error}", path.display())))?;
    write(path, &contents)
}

fn source(language: &str) -> (&'static str, &'static str) {
    match language {
        "rust" => ("lib.rs", "//! Replace with the miniature repository this case is about.\n\n#[cfg(test)]\nmod tests {\n    #[trace(\"TC-001\")]\n    #[test]\n    fn covers_the_criterion() {\n        assert_eq!(1 + 1, 2);\n    }\n}\n"),
        "python" => ("test_example.py", "def test_covers_the_criterion():\n    # TC-001: this tag names the matrix row.\n    assert 1 + 1 == 2\n"),
        _ => ("example.test.ts", "import { expect, it } from \"vitest\";\n\nit(\"TC-001 covers the criterion\", () => {\n  expect(1 + 1).toBe(2);\n});\n"),
    }
}

/// Scaffold one case or add a language variant to an existing case.
pub fn create(root: &Path, options: &Options<'_>) -> Result<(PathBuf, String), CorpusError> {
    if !["rust", "python", "typescript"].contains(&options.language) {
        return Err(invalid(format!(
            "unsupported language `{}`",
            options.language
        )));
    }
    if !["failure", "control", "regression"].contains(&options.kind) {
        return Err(invalid(format!("unsupported kind `{}`", options.kind)));
    }
    if options.case.is_empty()
        || options.case.contains('/')
        || options.case == "."
        || options.case == ".."
    {
        return Err(invalid("case name must be one nonempty path component"));
    }
    let declaration = load_yaml(&root.join("corpus.yaml"))?;
    if !declaration["mode_families"]
        .as_array()
        .is_some_and(|families| families.contains(&Value::String(options.mode.to_owned())))
    {
        return Err(invalid(format!(
            "`{}` is not a declared mode family",
            options.mode
        )));
    }
    let selector = module_selector(root, options.module)?;
    let case_id = if options.kind == "control" {
        format!("{}-control", options.case)
    } else {
        options.case.to_owned()
    };
    let case_dir = root.join("cases").join(options.mode).join(&case_id);
    let adding_language = case_dir.exists();
    let variant_dir;
    if adding_language {
        let shared_path = case_dir.join("case.yaml");
        let mut shared = load_yaml(&shared_path)?;
        for (field, expected) in [
            ("mode", options.mode),
            ("kind", options.kind),
            ("module", options.module),
        ] {
            if shared[field] != expected {
                return Err(invalid(format!(
                    "{}: declares {field}={}, not {expected}",
                    case_dir.display(),
                    shared[field]
                )));
            }
        }
        if case_dir.join("input").is_dir() {
            let old_language = shared["language"]
                .as_str()
                .ok_or_else(|| invalid("existing compact case has no language"))?
                .to_owned();
            if old_language == options.language {
                return Err(invalid(format!(
                    "{} already has {}",
                    case_dir.display(),
                    options.language
                )));
            }
            let old_dir = case_dir.join(&old_language);
            if old_dir.exists() {
                return Err(invalid(format!("{} already exists", old_dir.display())));
            }
            let relative = case_dir
                .strip_prefix(root)
                .map_err(|error| invalid(error.to_string()))?;
            let old_scope = format!("{}/input", relative.display());
            let new_scope = format!("{}/{old_language}/input", relative.display());
            let authored = shared["reproduce"]
                .as_str()
                .ok_or_else(|| invalid("existing compact case has no reproduce command"))?;
            if !authored.contains(&old_scope) {
                return Err(invalid(format!(
                    "existing reproduce command does not name `{old_scope}`"
                )));
            }
            let relocated = authored.replacen(&old_scope, &new_scope, 1);
            fs::create_dir(&old_dir).map_err(|error| invalid(error.to_string()))?;
            fs::rename(case_dir.join("input"), old_dir.join("input"))
                .map_err(|error| invalid(error.to_string()))?;
            if case_dir.join("expect.yaml").is_file() {
                fs::rename(case_dir.join("expect.yaml"), old_dir.join("expect.yaml"))
                    .map_err(|error| invalid(error.to_string()))?;
            }
            yaml_write(&old_dir.join("case.yaml"), &json!({"reproduce": relocated}))?;
            shared
                .as_object_mut()
                .ok_or_else(|| invalid("existing case.yaml is not a mapping"))?
                .remove("language");
            shared
                .as_object_mut()
                .ok_or_else(|| invalid("existing case.yaml is not a mapping"))?
                .remove("reproduce");
            yaml_write(&shared_path, &shared)?;
        }
        variant_dir = case_dir.join(options.language);
        if variant_dir.exists() {
            return Err(invalid(format!("{} already exists", variant_dir.display())));
        }
    } else {
        variant_dir = case_dir.clone();
    }
    fs::create_dir_all(variant_dir.join("input/spec"))
        .map_err(|error| invalid(error.to_string()))?;
    fs::create_dir_all(variant_dir.join("input/src"))
        .map_err(|error| invalid(error.to_string()))?;
    write(&variant_dir.join("input/spec/FR-001.md"), "---\nid: FR-001\ntype: FR\n---\n\n## Acceptance Criteria\n\n| ID | Criteria | Verification |\n|----|----------|--------------|\n| FR-001-AC-1 | Every finding shall default to warning. | Test (TC-001) |\n")?;
    write(&variant_dir.join("input/spec/tests.md"), "---\nid: TM-001\ntype: TestMatrix\n---\n\n## Test Case Summary\n\n| Test ID | Traces To | Status |\n|---------|-----------|--------|\n| TC-001 | FR-001-AC-1 | 🚧 |\n")?;
    let (filename, contents) = source(options.language);
    write(&variant_dir.join("input/src").join(filename), contents)?;
    let relative = variant_dir
        .strip_prefix(root)
        .map_err(|error| invalid(error.to_string()))?
        .to_path_buf();
    let scope = format!("{}/input", relative.display());
    let reproduce = if selector.starts_with("IX_") {
        format!("{selector} quire coverage --scope {scope} --json")
    } else {
        format!("quire coverage --scope {scope} {selector} --json")
    };
    if adding_language {
        yaml_write(
            &variant_dir.join("case.yaml"),
            &json!({"reproduce": reproduce}),
        )?;
    } else {
        let mut meta = json!({
            "id": case_id, "issue_ref": if options.issue.is_empty() { "REQUIRED — name the filing this case regresses" } else { options.issue },
            "mode": options.mode, "language": options.language, "module": options.module,
            "kind": options.kind, "findable": options.kind == "failure", "reproduce": reproduce,
            "tags": ["TC-REPLACE-ME"],
            "comment": "What this case is about, and the measurement that made it worth a fixture."
        });
        if options.kind == "failure" {
            meta["grading_contract"] = json!({"channel":"finding", "levels":{
                "L1":{"state":"required"}, "L2":{"state":"required"}, "L3":{"state":"required"}}});
        }
        if options.module != "ecosystem" {
            meta["relaxation_ticket"] =
                Value::String("REQUIRED — name the ticket this variant binding is sizing".into());
        }
        if options.kind == "control" {
            meta["control_for"] = json!([options.case]);
        }
        yaml_write(&case_dir.join("case.yaml"), &meta)?;
    }
    write(&variant_dir.join("expect.yaml"), "# Assert only what this case is about.\n# A failure asserts diagnostic_reasons; its control asserts absent_diagnostic_reasons.\n")?;
    Ok((relative, reproduce))
}

#[cfg(test)]
mod tests {
    use std::fs;

    use super::{create, Options};
    use crate::corpus::load_yaml;

    /// Trace: FR-065-AC-3, FR-065-AC-18. A control scaffold has usable metadata.
    #[test]
    fn control_scaffold_selects_module_path_and_lists_partner() {
        let root = tempfile::tempdir().expect("scratch corpus");
        fs::write(
            root.path().join("corpus.yaml"),
            "mode_families: [detection]\n",
        )
        .expect("declaration");
        let module = root.path().join("modules/ecosystem/spec-artifacts-iso");
        fs::create_dir_all(&module).expect("module directory");
        fs::write(module.join("manifest.yaml"), "id: iso\n").expect("manifest");
        let options = Options {
            mode: "detection",
            case: "example",
            language: "rust",
            kind: "control",
            module: "ecosystem",
            issue: "agent-ix/example#1",
        };
        let (relative, reproduce) = create(root.path(), &options).expect("scaffold control");
        assert_eq!(
            relative.to_string_lossy(),
            "cases/detection/example-control"
        );
        assert!(reproduce.starts_with("IX_FILAMENT_MODULES_PATH=modules/ecosystem quire coverage"));
        let meta = load_yaml(&root.path().join(relative).join("case.yaml")).expect("metadata");
        assert_eq!(meta["control_for"], serde_json::json!(["example"]));
        assert!(meta.get("case").is_none());
        assert_eq!(meta["findable"], false);
    }

    /// Trace: FR-065-AC-18. Adding a language keeps the first authored input.
    #[test]
    fn adding_language_moves_compact_input_into_its_variant() {
        let root = tempfile::tempdir().expect("scratch corpus");
        fs::write(
            root.path().join("corpus.yaml"),
            "mode_families: [detection]\n",
        )
        .expect("declaration");
        let module = root.path().join("modules/ecosystem/spec-artifacts-iso");
        fs::create_dir_all(&module).expect("module directory");
        fs::write(module.join("manifest.yaml"), "id: iso\n").expect("manifest");
        let mut options = Options {
            mode: "detection",
            case: "example",
            language: "rust",
            kind: "failure",
            module: "ecosystem",
            issue: "agent-ix/example#1",
        };
        create(root.path(), &options).expect("first language");
        options.language = "python";
        create(root.path(), &options).expect("second language");
        let case = root.path().join("cases/detection/example");
        assert!(case.join("rust/input/src/lib.rs").is_file());
        assert!(case.join("python/input/src/test_example.py").is_file());
        let shared = load_yaml(&case.join("case.yaml")).expect("shared metadata");
        assert!(shared.get("language").is_none());
        assert!(shared.get("reproduce").is_none());
        for language in ["rust", "python"] {
            let variant =
                load_yaml(&case.join(language).join("case.yaml")).expect("variant metadata");
            assert!(variant["reproduce"]
                .as_str()
                .is_some_and(|command| command.contains(language)));
        }
    }
}
