//! A line-oriented grammar: JSON-quoted strings, words, and # comments.
use serde_json::{json, Value};

#[derive(Debug)]
pub struct Suite {
    pub base_url: Option<String>,
    pub timeout: Option<u64>,
    pub before_each: Vec<Step>,
    pub tests: Vec<Test>,
}

#[derive(Debug)]
pub struct Test {
    pub name: String,
    pub line: usize,
    pub steps: Vec<Step>,
}

#[derive(Debug)]
pub struct Step {
    pub line: usize,
    pub source: String,
    pub method: &'static str,
    pub params: Value,
    pub assertion: Option<Assertion>,
}

#[derive(Debug)]
pub enum Assertion {
    Equals(Value),
    Contains(String),
}

#[derive(Debug)]
struct Token {
    value: String,
    quoted: bool,
}

fn tokens(mut line: &str) -> Result<Vec<Token>, String> {
    let mut out = Vec::new();
    loop {
        line = line.trim_start();
        if line.is_empty() || line.starts_with('#') {
            return Ok(out);
        }
        let quoted = line.starts_with('"');
        let (value, end) = if quoted {
            let mut escaped = false;
            let end = line.char_indices().skip(1).find_map(|(i, c)| {
                if escaped {
                    escaped = false;
                } else if c == '\\' {
                    escaped = true;
                } else if c == '"' {
                    return Some(i + 1);
                }
                None
            });
            let end = end.ok_or("unterminated string; use double quotes and JSON escapes")?;
            let value = serde_json::from_str::<String>(&line[..end])
                .map_err(|e| format!("invalid quoted string: {e}"))?;
            if line[end..]
                .chars()
                .next()
                .is_some_and(|c| !c.is_whitespace() && c != '#')
            {
                return Err("expected whitespace after quoted string".into());
            }
            (value, end)
        } else {
            let end = line
                .find(|c: char| c.is_whitespace() || c == '#')
                .unwrap_or(line.len());
            (line[..end].to_owned(), end)
        };
        out.push(Token { value, quoted });
        line = &line[end..];
    }
}

fn string(token: &Token) -> Result<String, String> {
    if token.quoted {
        Ok(token.value.clone())
    } else {
        Err(format!(
            "expected a double-quoted string, got {:?}",
            token.value
        ))
    }
}

fn number(token: &Token) -> Result<u64, String> {
    if token.quoted || !token.value.bytes().all(|b| b.is_ascii_digit()) {
        return Err("expected a non-negative integer".into());
    }
    token
        .value
        .parse()
        .map_err(|_| "integer is too large".into())
}

pub fn timeout(value: &str) -> Result<u64, String> {
    let value = number(&Token {
        value: value.into(),
        quoted: false,
    })?;
    if !(1..=3_600_000).contains(&value) {
        return Err("timeout must be between 1 and 3600000 milliseconds".into());
    }
    Ok(value)
}

fn step(t: &[Token], line: usize, source: &str) -> Result<Step, String> {
    let words: Vec<&str> = t.iter().map(|t| t.value.as_str()).collect();
    if t[0].quoted || (words[0] == "expect" && t.get(1).is_some_and(|t| t.quoted)) {
        return Err("command names must not be quoted".into());
    }
    let s = |i| string(&t[i]);
    let mut assertion = None;
    let (method, params) = match words.as_slice() {
        ["navigate", _] => ("navigate", json!({"url": s(1)?})),
        ["click", _] => ("click", json!({"selector": s(1)?})),
        ["hover", _] => ("hover", json!({"selector": s(1)?})),
        ["fill", _, _] => ("fill", json!({"selector": s(1)?, "value": s(2)?})),
        ["type", _, _] => ("type", json!({"selector": s(1)?, "text": s(2)?})),
        ["press", _] => ("press", json!({"key": s(1)?})),
        ["press", _, _] => ("press", json!({"selector": s(1)?, "key": s(2)?})),
        ["select", _, _] => ("select", json!({"selector": s(1)?, "value": s(2)?})),
        ["check" | "uncheck", _] => (
            "check",
            json!({"selector": s(1)?, "checked": words[0] == "check"}),
        ),
        ["upload", _, _] => ("upload", json!({"selector": s(1)?, "paths": [s(2)?]})),
        ["screenshot", _] => ("screenshot", json!({"path": s(1)?})),
        ["eval", _] => ("eval", json!({"expression": s(1)?})),
        ["reload"] => ("reload", json!({})),
        ["back"] => ("back", json!({})),
        ["forward"] => ("forward", json!({})),
        ["expect", "visible" | "hidden" | "attached", _] => {
            ("wait_for", json!({"selector": s(2)?, "state": words[1]}))
        }
        ["expect", "text" | "contains", _, _] => {
            assertion = Some(if words[1] == "text" {
                Assertion::Equals(json!(s(3)?))
            } else {
                Assertion::Contains(s(3)?)
            });
            ("text", json!({"selector": s(2)?}))
        }
        ["expect", "title" | "url" | "url_contains", _] => {
            assertion = Some(if words[1] == "url_contains" {
                Assertion::Contains(s(2)?)
            } else {
                Assertion::Equals(json!(s(2)?))
            });
            (if words[1] == "title" { "title" } else { "url" }, json!({}))
        }
        ["expect", "count", _, _] => {
            assertion = Some(Assertion::Equals(json!(number(&t[3])?)));
            ("count", json!({"selector": s(2)?}))
        }
        ["expect", "attr", _, _, _] => {
            assertion = Some(Assertion::Equals(json!(s(4)?)));
            ("attr", json!({"selector": s(2)?, "name": s(3)?}))
        }
        ["expect", "js", _] => {
            assertion = Some(Assertion::Equals(json!(true)));
            ("eval", json!({"expression": s(2)?}))
        }
        _ => {
            return Err(format!(
                "unknown command or wrong arguments: {source}; see bruster test --help"
            ))
        }
    };
    Ok(Step {
        line,
        source: source.trim().into(),
        method,
        params,
        assertion,
    })
}

pub fn parse(source: &str) -> Result<Suite, String> {
    let mut suite = Suite {
        base_url: None,
        timeout: None,
        before_each: Vec::new(),
        tests: Vec::new(),
    };
    let mut block: Option<Test> = None;
    let mut before = false;
    let mut seen_before = false;
    for (index, source) in source.trim_start_matches('\u{feff}').lines().enumerate() {
        let line = index + 1;
        let parse_line = |error| format!("{line}: {error}");
        let t = tokens(source).map_err(parse_line)?;
        if t.is_empty() {
            continue;
        }
        let words: Vec<&str> = t.iter().map(|t| t.value.as_str()).collect();
        let result: Result<(), String> = (|| {
            if t[0].quoted {
                return Err("command names must not be quoted".into());
            }
            match words.as_slice() {
                ["end"] => {
                    let test = block.take().ok_or("end without test or before_each")?;
                    if test.steps.is_empty() {
                        return Err("empty test or before_each block".into());
                    }
                    if before {
                        suite.before_each = test.steps;
                    } else {
                        suite.tests.push(test);
                    }
                    before = false;
                }
                ["test", _] | ["before_each"] => {
                    if block.is_some() {
                        return Err("missing end before the next block".into());
                    }
                    before = words[0] == "before_each";
                    let name = if before {
                        if seen_before {
                            return Err("only one before_each block is allowed per file".into());
                        }
                        seen_before = true;
                        "before_each".into()
                    } else {
                        string(&t[1])?
                    };
                    if name.trim().is_empty() {
                        return Err("test name must not be empty".into());
                    }
                    if !before && suite.tests.iter().any(|test| test.name == name) {
                        return Err(format!("duplicate test name: {name:?}"));
                    }
                    block = Some(Test {
                        name,
                        line,
                        steps: Vec::new(),
                    });
                }
                ["base_url", _] if block.is_none() => {
                    if suite.base_url.is_some() {
                        return Err("duplicate base_url".into());
                    }
                    suite.base_url = Some(string(&t[1])?);
                }
                ["timeout", _] if block.is_none() => {
                    if suite.timeout.is_some() {
                        return Err("duplicate timeout".into());
                    }
                    number(&t[1])?;
                    suite.timeout = Some(timeout(&t[1].value)?);
                }
                _ => {
                    let block = block
                        .as_mut()
                        .ok_or("steps must be inside test or before_each")?;
                    block.steps.push(step(&t, line, source)?);
                }
            }
            Ok(())
        })();
        result.map_err(parse_line)?;
    }
    if let Some(block) = block {
        return Err(format!("{}: missing end for {:?}", block.line, block.name));
    }
    if suite.tests.is_empty() {
        return Err("1: file contains no tests".into());
    }
    Ok(suite)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strings_comments_and_source_locations() {
        let suite = parse("\u{feff}# comment\r\nbase_url \"http://localhost:3000\"\r\ntimeout 1000\r\nbefore_each\r\n navigate \"/\"\r\nend\r\ntest \"日本 # greeting\"\r\n fill \"#name\" \"Ada \\\"A\\\"\\nLovelace\" # comment\r\n expect text \"#out\" \"hi # Ada\"\r\nend").unwrap();
        assert_eq!(suite.tests[0].name, "日本 # greeting");
        assert_eq!(suite.tests[0].steps[0].line, 8);
        assert_eq!(
            suite.tests[0].steps[0].params["value"],
            "Ada \"A\"\nLovelace"
        );
        assert_eq!(suite.before_each[0].params["url"], "/");
        assert_eq!(suite.timeout, Some(1000));
    }

    #[test]
    fn rejects_ambiguous_or_incomplete_files() {
        for (source, diagnostic) in [
            ("test \"a\"\nclick \"#a\"", "missing end"),
            ("test \"a\"\nend", "empty test"),
            ("test \"a\"\nclik \"#a\"\nend", "2: unknown command"),
            ("test \"a\"\nclick #a\nend", "2: unknown command"),
            (
                "test \"a\"\nfill \"#a\"\"b\"\nend",
                "2: expected whitespace",
            ),
            ("test \"a\"\nclick \"#a\nend", "2: unterminated"),
            ("test \"a\"\nclick \"\\q\"\nend", "2: invalid quoted"),
            (
                "test \"a\"\nexpect count \"li\" -1\nend",
                "non-negative integer",
            ),
            (
                "test \"a\"\nexpect \"text\" \"p\" \"hi\"\nend",
                "must not be quoted",
            ),
            ("timeout 0\ntest \"a\"\nreload\nend", "timeout must be"),
            ("end", "end without"),
            ("navigate \"/\"", "steps must be inside"),
            ("# no tests", "file contains no tests"),
            (
                "test \"a\"\nreload\nend\ntest \"a\"\nreload\nend",
                "duplicate test",
            ),
            ("test \"a\"\ntest \"b\"", "missing end before"),
        ] {
            assert!(
                parse(source).unwrap_err().contains(diagnostic),
                "{source:?}: expected {diagnostic}"
            );
        }
    }
}
