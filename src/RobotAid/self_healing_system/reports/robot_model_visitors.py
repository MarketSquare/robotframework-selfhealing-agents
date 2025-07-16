from typing import Any, List, Tuple

from robot.api.parsing import ModelTransformer
from robot.parsing.model import VariableSection


class LocatorReplacer(ModelTransformer):
    """AST transformer that replaces locator tokens in keyword calls."""

    def __init__(self, replacements: List[Tuple[str, str]]) -> None:
        """Initialize with mapping of old to new locator strings.

        Args:
            replacements: List of (old_locator, new_locator) pairs.
        """
        super().__init__()
        self.replacements: dict[str, str] = dict(replacements)

    def visit_KeywordCall(self, node: Any) -> Any:
        """Replace matching token values in a KeywordCall node.

        Args:
            node: A Robot Framework AST KeywordCall node.

        Returns:
            The modified node with locators replaced.
        """
        for token in node.tokens[1:]:
            if token.value in self.replacements:
                token.value = self.replacements[token.value]
        return node


class VariablesReplacer(ModelTransformer):
    """AST transformer that replaces variable definitions in resource files."""

    def __init__(self, replacements: List[Tuple[str, str]]) -> None:
        """Initialize with mapping of variable names to new values.

        Args:
            replacements: List of (variable_name, new_value) pairs.
        """
        super().__init__()
        self.replacements: dict[str, str] = dict(replacements)

    def visit_VariableSection(self, node: VariableSection) -> Any:
        """Replace variable values in the VariableSection of a resource.

        Args:
            node: The VariableSection node from a resource file.

        Returns:
            The node with variables replaced where applicable.
        """
        for variable in node.body:
            name_token: str = variable.tokens[0].value
            if name_token in self.replacements:
                variable.tokens[2].value = self.replacements[name_token]
        return self.generic_visit(node)
