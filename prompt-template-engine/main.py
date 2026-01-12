"""Prompt template engine - variable substitution with partial application, plus interchangeable
render strategies (plain, few-shot, chat) for turning a template into what the model actually sees."""

from abc import ABC, abstractmethod
from string import Formatter


class PromptTemplate:
    """A template string with named `{placeholders}`. `partial` binds a subset of variables ahead
    of time and returns a new template, so callers can build up context in stages without mutating
    a shared instance."""

    def __init__(self, template: str, **bound):
        self.template = template
        self._bound = bound

    def partial(self, **kwargs) -> "PromptTemplate":
        return PromptTemplate(self.template, **{**self._bound, **kwargs})

    def variables(self) -> set[str]:
        return {name for _, name, _, _ in Formatter().parse(self.template) if name}

    def format(self, **kwargs) -> str:
        merged = {**self._bound, **kwargs}
        missing = self.variables() - merged.keys()
        if missing:
            raise KeyError(f"missing template variables: {sorted(missing)}")
        return self.template.format(**merged)


class RenderStrategy(ABC):
    @abstractmethod
    def render(self, template: PromptTemplate, **kwargs):
        ...


class PlainRenderStrategy(RenderStrategy):
    """Straight substitution into a single string, no extra structure."""

    def render(self, template: PromptTemplate, **kwargs) -> str:
        return template.format(**kwargs)


class FewShotRenderStrategy(RenderStrategy):
    """Renders each example through `example_template`, then the real query through `template`,
    joined into one string - the standard few-shot prompt shape."""

    def __init__(self, examples: list[dict], example_template: PromptTemplate):
        self.examples = examples
        self.example_template = example_template

    def render(self, template: PromptTemplate, **kwargs) -> str:
        rendered_examples = [self.example_template.format(**ex) for ex in self.examples]
        query = template.format(**kwargs)
        return "\n\n".join([*rendered_examples, query])


class ChatRenderStrategy(RenderStrategy):
    """Renders into a list of {role, content} messages instead of a single string, with an
    optional system message rendered from its own template."""

    def __init__(self, system_template: PromptTemplate | None = None):
        self.system_template = system_template

    def render(self, template: PromptTemplate, **kwargs) -> list[dict]:
        messages = []
        if self.system_template is not None:
            messages.append({"role": "system", "content": self.system_template.format(**kwargs)})
        messages.append({"role": "user", "content": template.format(**kwargs)})
        return messages


def main():
    # Partial application: bind the instruction once, reuse the bound template for every review.
    review_template = PromptTemplate("{instruction}\nReview: {text}\nSentiment:")
    bound_template = review_template.partial(
        instruction="Classify the sentiment of this review as positive, negative, or neutral."
    )
    print(f"template variables: {sorted(review_template.variables())}")
    print("partial() bound 'instruction' - only 'text' is needed at render time\n")

    print("-- plain render --")
    plain = PlainRenderStrategy()
    print(plain.render(bound_template, text="The battery life is incredible, I'm impressed."))

    print("\n-- few-shot render --")
    example_template = PromptTemplate("Review: {text}\nSentiment: {label}")
    examples = [
        {"text": "Terrible customer service, never buying again.", "label": "negative"},
        {"text": "It's fine, does what it says on the box.", "label": "neutral"},
    ]
    few_shot = FewShotRenderStrategy(examples, example_template)
    query_only = PromptTemplate("Review: {text}\nSentiment:")
    print(few_shot.render(query_only, text="The battery life is incredible, I'm impressed."))

    print("\n-- chat render --")
    system_template = PromptTemplate("You are a terse sentiment classifier. Reply with one word.")
    chat = ChatRenderStrategy(system_template=system_template)
    messages = chat.render(query_only, text="The battery life is incredible, I'm impressed.")
    for msg in messages:
        print(f"  {msg}")


if __name__ == "__main__":
    main()
