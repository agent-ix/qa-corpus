fn validate_artifact_path(artifact: String) -> Result<String, ShellOpenError> {
    let normalized = artifact.replace('\\', "/");
    if normalized.is_empty()
        || normalized.starts_with('/')
        || normalized.contains('\0')
        || normalized
            .split('/')
            .any(|segment| segment.is_empty() || segment == "." || segment == "..")
    {
        return Err(ShellOpenError::root_refused("outside root"));
    }
    Ok(normalized)
}
