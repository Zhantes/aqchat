from pathlib import Path
from typing import List
from pipelines.boundary_splitter import CodeBoundaryTextSplitter
from pipelines.detectors import CodeBoundaryDetector, RustBoundaryDetector

def _get_test_code_and_detector() -> str | None:
    code = Path(f"test_data/splitting/sample_rs.rs").read_text("utf-8")
    detector = RustBoundaryDetector()
    
    return code, detector

def _split_with_detector(code: str, detector: CodeBoundaryDetector) -> List[str]:
    splitter = CodeBoundaryTextSplitter()
    chunks = [chunk.strip() for chunk in splitter.split_text(code, boundary_detector=detector)]
    return chunks

def test_rust_imports():
    """This tests if the splitter can successfully split imports
    at the top of the code file.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """//! @brief A simple logging system with pluggable output backends.
//!
//! This demonstrates basic use of structs, traits, imports, and decorators.

use std::fmt;
use std::time::{SystemTime, UNIX_EPOCH};"""
    
    assert expected in result

def test_rust_func_isolated():
    """This tests if the splitter can successfully split a function
    which is not within an impl.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """/// @brief A utility function to send a log message.
fn log_message<B: LogBackend>(backend: &B, level: LogLevel, content: &str) {
    let msg = LogMessage {
        timestamp: current_timestamp(),
        level,
        content: content.to_string(),
    };

    backend.log(&msg);
}"""
    
    assert expected in result

def test_rust_struct_decorated():
    """This tests if the splitter can successfully split a struct.
    The splitter should also handle decorators and comments.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """/// @brief A simple structure representing a log message.
#[derive(Debug)]
struct LogMessage {
    timestamp: u64,
    level: LogLevel,
    content: String,
}"""

    assert expected in result

def test_rust_impl():
    """This tests if the splitter can successfully split an impl,
    including function definitions that sit inside.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """impl fmt::Display for LogMessage {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "[{}][{:?}] {}",
            self.timestamp,
            self.level,
            self.content
        )
    }
}"""
    
    assert expected in result

def test_rust_impl_decorated():
    """This tests if the splitter can successfully split an impl,
    even if the impl has a preceding comment/decorator.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """/// @allow(dead_code)
impl ConsoleLogger {
    /// @brief Create a new ConsoleLogger.
    fn new() -> Self {
        ConsoleLogger
    }
}"""
    
    assert expected in result

def test_rust_func_impl():
    """This tests if the splitter can successfully split a function
    that sits inside an impl.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "[{}][{:?}] {}",
            self.timestamp,
            self.level,
            self.content
        )
    }"""
    
    assert expected in result

def test_rust_trait():
    """This tests if the splitter can successfully split a trait.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """/// @brief A trait for anything that can handle log messages.
trait LogBackend {
    /// @brief Handle a log message.
    fn log(&self, message: &LogMessage);
}"""
    
    assert expected in result

def test_rust_struct_decl():
    """This tests if the splitter can successfully split a
    struct without any members.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """/// @brief A backend that logs messages to stdout.
struct ConsoleLogger;"""
    
    assert expected in result

    