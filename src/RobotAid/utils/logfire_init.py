def init_logfire():
    try:
        import logfire

        def scrubbing_callback(m: logfire.ScrubMatch):
            """Callback function for scrubbing sensitive data in logfire.

            Args:
                m: ScrubMatch object containing pattern match information.

            Returns:
                The value if specific patterns match, None otherwise.
            """
            if (
                m.path == ("attributes", "all_messages_events", 0, "content")
                and m.pattern_match.group(0) == "Password"
            ):
                return m.value

            if (
                m.path == ("attributes", "all_messages_events", 1, "content")
                and m.pattern_match.group(0) == "credit-card"
            ):
                return m.value

        logfire.configure(scrubbing=logfire.ScrubbingOptions(callback=scrubbing_callback))

        logfire.instrument_pydantic_ai()
    except ImportError:
        print("Logfire is not installed. Skipping logfire configuration.")
