fn escapes_the_root(artifact: &str) -> bool {
    let normalized = artifact.replace('\\', "/");
    normalized.is_empty()
        || normalized.starts_with('/')
        || normalized.contains('\0')
        || normalized
            .split('/')
            .any(|segment| segment.is_empty() || segment == "." || segment == "..")
}

#[trace("TC-001")]
#[test]
fn tc1598_artifact_acceptance_matches_the_containment_rule() {
    let artifact = "C:\\Windows";
    let accepted = OpenRequest::new("/tmp/project", artifact.clone()).is_ok();
    prop_assert_eq!(accepted, !escapes_the_root(&artifact));
}
