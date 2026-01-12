# Prompt Template Engine

## Problem
Design a templating system for LLM prompts: variable substitution with named placeholders, the
ability to pre-bind some variables and defer the rest (partial application), and multiple ways to
turn the same template into what actually gets sent to a model - a single string, a few-shot prompt
with worked examples, or a chat-format message list.

## Design
- `PromptTemplate` - a template string with `{name}` placeholders. `variables()` inspects the
  template for its placeholder names; `format(**kwargs)` substitutes and raises if anything required
  is missing; `partial(**kwargs)` binds a subset of variables and returns a new, independent
  template so the original is never mutated.
- `RenderStrategy` (ABC) - defines `render(template, **kwargs)`, the single contract every render
  mode implements.
- `PlainRenderStrategy` - direct substitution into one string.
- `FewShotRenderStrategy` - renders a list of examples through a separate `example_template`, then
  the real query, joined into one prompt.
- `ChatRenderStrategy` - renders into a `[{role, content}, ...]` message list, with an optional
  system message from its own template.

## Patterns used
- **Strategy** - `RenderStrategy` implementations are interchangeable rendering algorithms; the
  caller picks one at construction time without changing how `PromptTemplate.format` works.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/prompt-template-engine
python3 main.py
```
