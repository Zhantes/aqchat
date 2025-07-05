//! @brief A simple logging system with pluggable output backends.
//!
//! This demonstrates basic use of structs, traits, imports, and decorators.

use std::fmt;
use std::time::{SystemTime, UNIX_EPOCH};

/// @brief Get the current Unix timestamp in seconds.
fn current_timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_secs()
}

/// @brief Levels of logging severity.
#[derive(Debug, Clone, Copy)]
enum LogLevel {
    Info,
    Warning,
    Error,
}

/// @brief A simple structure representing a log message.
#[derive(Debug)]
struct LogMessage {
    timestamp: u64,
    level: LogLevel,
    content: String,
}

impl fmt::Display for LogMessage {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "[{}][{:?}] {}",
            self.timestamp,
            self.level,
            self.content
        )
    }
}

/// @brief A trait for anything that can handle log messages.
trait LogBackend {
    /// @brief Handle a log message.
    fn log(&self, message: &LogMessage);
}

/// @brief A backend that logs messages to stdout.
struct ConsoleLogger;

/// @allow(dead_code)
impl ConsoleLogger {
    /// @brief Create a new ConsoleLogger.
    fn new() -> Self {
        ConsoleLogger
    }
}

impl LogBackend for ConsoleLogger {
    fn log(&self, message: &LogMessage) {
        println!("{}", message);
    }
}

/// @brief A utility function to send a log message.
fn log_message<B: LogBackend>(backend: &B, level: LogLevel, content: &str) {
    let msg = LogMessage {
        timestamp: current_timestamp(),
        level,
        content: content.to_string(),
    };

    backend.log(&msg);
}

/// @brief Entry point for the program.
fn main() {
    let logger = ConsoleLogger::new();

    log_message(&logger, LogLevel::Info, "Application started");
    log_message(&logger, LogLevel::Warning, "Low disk space");
    log_message(&logger, LogLevel::Error, "Unable to open file");
}
