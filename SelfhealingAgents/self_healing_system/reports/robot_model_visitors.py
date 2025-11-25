from typing import Any, Dict, List, Tuple

from robot.api.parsing import ModelTransformer
from robot.parsing.model import VariableSection

from SelfhealingAgents.self_healing_system.schemas.internal_state.locator_replacements import LocatorReplacements
from SelfhealingAgents.self_healing_system.reports.locator_argument_analyzer import (
    ArgumentAnalysisResult,
    analyze_locator_argument,
)


class LocatorReplacer(ModelTransformer):
    """AST transformer for replacing locator tokens in Robot Framework keyword calls.

    This class traverses the Robot Framework AST and replaces specified locator
    strings in keyword call arguments with new values, as defined by the replacements mapping.

    Attributes:
        _replacements (Dict[str, str]): Mapping of old locator strings to their new values.
    """
    def __init__(self, replacements: List[LocatorReplacements]) -> None:
        """Initializes the LocatorReplacer with a mapping of locator replacements.

        Args:
            replacements: A list of (old_locator, new_locator) pairs specifying which
                locator strings should be replaced and their corresponding new values.
        """
        super().__init__()
        self._replacements: List[LocatorReplacements] = replacements
        self._processed: set[int] = set()
        self.variable_updates: Dict[str, str] = {}

    def visit_KeywordCall(self, node: Any) -> Any:
        """Replaces matching locator tokens in a KeywordCall node.

        Iterates over the tokens in the given KeywordCall node and replaces any
        token value that matches an old locator with its corresponding new value.

        Args:
            node: A Robot Framework AST KeywordCall node.

        Returns:
            The modified KeywordCall node with locator tokens replaced where applicable.
        """
        for token in node.tokens[1:]:
            for repl in self._replacements:
                repl_id = id(repl)
                if repl_id in self._processed:
                    continue

                raw_locator_arg: str | None = None
                if repl.keyword_args:
                    raw_locator_arg = repl.keyword_args[0]

                if raw_locator_arg:
                    if token.value.strip() != raw_locator_arg.strip():
                        continue
                else:
                    if token.value != repl.failed_locator:
                        continue

                analysis: ArgumentAnalysisResult = analyze_locator_argument(
                    raw_argument=raw_locator_arg or token.value,
                    failed_locator=repl.failed_locator,
                    healed_locator=repl.healed_locator,
                )
                token.value = analysis.token_value
                for name, value in analysis.variable_updates:
                    self.variable_updates[name] = value
                self._processed.add(repl_id)
        return node


class VariablesReplacer(ModelTransformer):
    """AST transformer for replacing variable definitions in Robot Framework resource files.

    This class traverses the VariableSection of a resource file and replaces variable
    values according to the provided replacements mapping.

    Attributes:
        _replacements (Dict[str, str]): Mapping of variable names to their new values.
    """
    def __init__(self, replacements: List[Tuple[str, str]]) -> None:
        """Initializes the VariablesReplacer with a mapping of variable replacements.

        Args:
            replacements: A list of (variable_name, new_value) pairs specifying which
                variable names should be replaced and their corresponding new values.
        """
        super().__init__()
        self._replacements: Dict[str, str] = {
            name: value for name, value in replacements if name and value is not None
        }

    def visit_VariableSection(self, node: VariableSection) -> Any:
        """Replaces variable values in the VariableSection node.

        Iterates over the variables in the VariableSection and updates their values
        if their names match any in the replacements mapping.

        Args:
            node: The VariableSection node from a Robot Framework resource file.

        Returns:
            The modified VariableSection node with variable values replaced where applicable.
        """
        for variable in node.body:
            try:
                name_token: str = variable.tokens[0].value
                if name_token in self._replacements:
                    # Variable values start at index 2 (arguments) – update each.
                    for idx in range(2, len(variable.tokens) - 1):
                        if variable.tokens[idx].type == "ARGUMENT":
                            variable.tokens[idx].value = self._replacements[name_token]
                            break
            except Exception:
                pass
        return self.generic_visit(node)
