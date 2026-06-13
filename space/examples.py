"""Demo inputs for the Gradio Space."""

EXAMPLE_WEBINAR = {
    "platform": "Telegram",
    "goal": "Register attendees for Thursday 7pm webinar",
    "audience": "Product managers who own product metrics",
    "post": (
        "Webinar on product metrics 🚀🚀 Link in bio!!! "
        "#product #metrics #growth #pm #webinar #training #analytics"
    ),
}

EXAMPLE_CHAT_DUMP = {
    "platform": "Telegram",
    "goal": (
        "Activate participants on 3 actions: read materials, write their own "
        "conduit version, refine the schema"
    ),
    "audience": "Working group on decision methodology — colleagues in context",
    "post": """Handbook (https://example.com/handbook) with checklists

[6/5/26 5:10 PM] Pavel Trubin:
Conduit zero-version:
- fragment one with typos and missing context
- another fragment referencing ontology without link

Please improve this conduit and turn it into a schema. Substantive thoughts go on the miro board.

Any and all important decisions will be made one way or another — complexity sits on both sides of the moment.""",
}
