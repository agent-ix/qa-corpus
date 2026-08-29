fn escapes_the_root(artifact: &str) -> bool {
    let mut depth = 0isize;
    for segment in artifact.replace('\\', "/").split('/') {
        depth += if segment == ".." { -1 } else { 1 };
        if depth < 0 {
            return true;
        }
    }
    false
}

#[trace("TC-001")]
#[test]
fn tc1598_artifact_acceptance_matches_the_containment_rule() {
    let artifact = "C:\\Windows";
    let accepted = OpenRequest::new("/tmp/project", artifact.clone()).is_ok();
    prop_assert_eq!(accepted, !escapes_the_root(&artifact));
}
