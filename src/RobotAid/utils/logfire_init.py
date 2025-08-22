from typing import Optional


def init_logfire() -> None:
    """
    Initialize Logfire with CI-safe defaults and custom scrubbing.

    Behavior:
        - Imports Logfire lazily so the application can run without it.
        - Registers a scrubbing callback that selectively unsanitizes known
          demo values ("Password", "credit-card") from specific paths.
        - Configures Logfire to send data only if a token is present; if a
          configuration error occurs, disables sending entirely.
        - Attempts to instrument Pydantic AI; failures are ignored.

    This function never raises if Logfire is missing or misconfigured, which
    makes it safe to call in CI environments without tokens.

    Returns:
        None
    """
    try:
        import logfire
        from logfire.exceptions import LogfireConfigError

        def scrubbing_callback(m: logfire.ScrubMatch) -> Optional[str]:
            """
            Selectively return matched values for known, non-sensitive demos.

            Args:
                m: The Logfire ScrubMatch describing the match, including
                   its path, the regex match object, and the original value.

            Returns:
                The original matched value to bypass scrubbing for the
                whitelisted demo fields, or None to keep the default scrubbing.
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
            return None

        try:
            logfire.configure(
                send_to_logfire="if-token-present",
                scrubbing=logfire.ScrubbingOptions(callback=scrubbing_callback),
                console=logfire.ConsoleOptions(show_project_link=False),
            )
        except LogfireConfigError:
            logfire.configure(
                send_to_logfire=False,
                scrubbing=logfire.ScrubbingOptions(callback=scrubbing_callback),
                console=logfire.ConsoleOptions(show_project_link=False),
            )

        try:
            logfire.instrument_pydantic_ai()
        except Exception:
            pass
    except ImportError:
        print("Logfire is not installed. Skipping logfire configuration.")
