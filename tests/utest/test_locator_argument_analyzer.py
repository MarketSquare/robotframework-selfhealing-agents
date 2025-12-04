from SelfhealingAgents.self_healing_system.reports.locator_argument_analyzer import (
    analyze_locator_argument,
)


def test_analyzer_updates_variable_when_suffix_same() -> None:
    result = analyze_locator_argument(
        raw_argument="${MAIN_SELECTOR} img",
        failed_locator="article.old img",
        healed_locator="article.new img",
    )

    assert result.token_value == "${MAIN_SELECTOR} img"
    assert result.variable_updates == [("${MAIN_SELECTOR}", "article.new")]


def test_analyzer_updates_literal_when_variable_same() -> None:
    result = analyze_locator_argument(
        raw_argument="${MAIN_SELECTOR} img",
        failed_locator="article.locator img",
        healed_locator="article.locator svg",
    )

    assert result.token_value == "${MAIN_SELECTOR} svg"
    assert result.variable_updates == []


def test_analyzer_handles_both_parts_changed() -> None:
    result = analyze_locator_argument(
        raw_argument="${MAIN_SELECTOR} img",
        failed_locator="article.old img",
        healed_locator="article.new picture",
    )

    assert result.token_value.endswith("picture")
    assert result.variable_updates
    assert result.variable_updates[0][0] == "${MAIN_SELECTOR}"


def test_analyzer_falls_back_to_literal_when_no_variable() -> None:
    result = analyze_locator_argument(
        raw_argument=".product-card",
        failed_locator=".product-card",
        healed_locator=".product-card-new",
    )

    assert result.token_value == ".product-card-new"
    assert result.variable_updates == []
