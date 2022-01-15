# Logging Framework

## Problem
Build a logging framework where a log message travels down a chain of handlers (console, file, alerting, ...), and each handler only processes messages at or above its own configured severity. The chain should be assembled once and reused for every log call.

## Design
- `Level` (enum) - `DEBUG`, `INFO`, `ERROR` with an ordinal-based `severity` used to compare messages against a handler's threshold.
- `Logger` (abstract) - holds a `level` and a reference to the `next` handler; its `log()` method writes the message if the handler's level qualifies, then always forwards to `next` so downstream handlers get a chance too.
- `ConsoleLogger`, `FileLogger`, `AlertLogger` - concrete handlers, each just implementing `write()`. `FileLogger` simulates writing to disk by printing with a `[FILE]` prefix instead of touching the filesystem, to keep the demo self-contained.

## Patterns used
- **Chain of Responsibility** - each handler decides independently whether to act on a message and then passes it along a linked chain, so adding a new handler (e.g. a Slack alert) means writing one class and re-wiring the chain, not touching existing handlers.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/logging-framework
java Main.java
```
