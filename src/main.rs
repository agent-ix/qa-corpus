//! Command-line gates and evidence producers for the controlled QA corpus.

use std::{env, path::PathBuf, process::ExitCode};

use qa_corpus::{bounds, corpus, external, reporting, scaffold, verify};

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = env::args().skip(1);
    let command = args
        .next()
        .ok_or("usage: qa-corpus <bounds|metadata|verify|verify-reporting|external-channel|new-case> [options]")?;
    let mut root = PathBuf::from(".");
    let mut json = false;
    let mut complete = false;
    let mut mode = None;
    let mut case = None;
    let mut language = String::from("rust");
    let mut kind = String::from("failure");
    let mut module = String::from("ecosystem");
    let mut issue = String::new();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--json" => json = true,
            "--require-complete" => complete = true,
            "--root" => root = PathBuf::from(args.next().ok_or("--root requires a directory")?),
            "--mode" => mode = Some(args.next().ok_or("--mode requires a value")?),
            "--case" => case = Some(args.next().ok_or("--case requires a value")?),
            "--language" => language = args.next().ok_or("--language requires a value")?,
            "--kind" => kind = args.next().ok_or("--kind requires a value")?,
            "--module" => module = args.next().ok_or("--module requires a value")?,
            "--issue" => issue = args.next().ok_or("--issue requires a value")?,
            _ => return Err(format!("unknown argument: {arg}").into()),
        }
    }
    match command.as_str() {
        "metadata" => {
            let cases = corpus::discover(&root)?;
            println!("validated {} cases", cases.len());
        }
        "bounds" => {
            let cases = corpus::discover(&root)?;
            let report = bounds::derive(&root, &cases)?;
            if complete {
                bounds::require_complete(&report)?;
            }
            if json {
                println!("{}", serde_json::to_string(&report)?);
            } else {
                let summary = &report["bounds"];
                println!("fixtures on disk: {}", cases.len());
                println!("declared cells: {}", summary["declared_cells"]);
                println!("covered: {}", summary["covered_count"]);
                println!("out-of-scope: {}", summary["out_of_scope_count"]);
                println!("GAP: {}", summary["gap_count"]);
            }
        }
        "external-channel" => {
            let cases = corpus::discover(&root)?;
            println!("{}", external::validate(&root, &cases)?);
        }
        "new-case" => {
            let options = scaffold::Options {
                mode: mode.as_deref().ok_or("new-case requires --mode")?,
                case: case.as_deref().ok_or("new-case requires --case")?,
                language: &language,
                kind: &kind,
                module: &module,
                issue: &issue,
            };
            let (relative, reproduce) = scaffold::create(&root, &options)?;
            println!("scaffolded {}", relative.display());
            println!("  run it:  {reproduce}");
            println!("  then: fill expect.yaml from what it printed, and set issue_ref");
        }
        "verify" => {
            let quire = env::var_os("QUIRE")
                .filter(|value| !value.is_empty())
                .map(PathBuf::from)
                .ok_or("verify: set QUIRE to the binary to test")?;
            let quoin = env::var_os("QUOIN")
                .filter(|value| !value.is_empty())
                .map(PathBuf::from);
            let summary = verify::verify(&root, &quire, quoin.as_deref())?;
            println!("engine: {}", summary.engine);
            println!("cases run: {}/{}", summary.ran, summary.total);
            println!("differential pairs graded: {}", summary.pairs);
            for failure in &summary.failures {
                println!("  MISMATCH {failure}");
            }
            println!("mismatches: {}", summary.failures.len());
            for (id, ticket, details) in &summary.pending {
                println!("  PENDING {id} ({ticket}) — expected to fail, and did:");
                for detail in details {
                    println!("      {detail}");
                }
            }
            if !summary.pending.is_empty() {
                println!("pending: {} case(s) awaiting a fix", summary.pending.len());
            }
            for (id, ticket) in &summary.stale {
                println!(
                    "  STALE {id} now PASSES — {ticket} appears to have landed. Remove `pending:`."
                );
            }
            if !summary.failures.is_empty() || !summary.stale.is_empty() {
                return Err("verification failed".into());
            }
        }
        "verify-reporting" => {
            let quoin = env::var_os("QUOIN")
                .filter(|value| !value.is_empty())
                .map(PathBuf::from)
                .ok_or("verify-reporting: set QUOIN to the Quoin executable")?;
            let summary = reporting::verify(&root, &quoin)?;
            println!("reporting cases run: {0}/{0}", summary.cases);
            for failure in &summary.failures {
                println!("  MISMATCH {failure}");
            }
            println!("reporting mismatches: {}", summary.failures.len());
            if !summary.failures.is_empty() {
                return Err("reporting verification failed".into());
            }
        }
        _ => return Err(format!("unknown command: {command}").into()),
    }
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("corpus: {error}");
            ExitCode::FAILURE
        }
    }
}
