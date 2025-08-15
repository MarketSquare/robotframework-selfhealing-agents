def init_logfire():
    """Initializes Logfire logging with custom scrubbing for sensitive data.

    Attempts to import and configure the Logfire library. If Logfire is not installed,
    the configuration is skipped. Sets up a custom scrubbing callback to handle
    sensitive data patterns in log messages and instruments Pydantic AI for logging.
    """
    try:
        import logfire

        def scrubbing_callback(m: logfire.ScrubMatch):
            """Callback for scrubbing sensitive data in Logfire logs.

            This function is invoked by Logfire when a potential sensitive data match
            is found. It checks the match path and pattern, and returns the value if
            specific patterns are matched.

            Args:
                m: A ScrubMatch object containing information about the matched pattern.

            Returns:
                The matched value if the path and pattern correspond to known sensitive
                data fields, otherwise None.
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
