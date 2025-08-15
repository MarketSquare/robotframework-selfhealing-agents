from typing import Any, List, Tuple, Dict

from robot.api.parsing import ModelTransformer
from robot.parsing.model import VariableSection


class LocatorReplacer(ModelTransformer):
    """AST transformer for replacing locator tokens in Robot Framework keyword calls.

    This class traverses the Robot Framework AST and replaces specified locator
    strings in keyword call arguments with new values, as defined by the replacements mapping.

    Attributes:
        _replacements (Dict[str, str]): Mapping of old locator strings to their new values.
    """
    def __init__(self, replacements: List[Tuple[str, str]]) -> None:
        """Initializes the LocatorReplacer with a mapping of locator replacements.

        Args:
            replacements: A list of (old_locator, new_locator) pairs specifying which
                locator strings should be replaced and their corresponding new values.
        """
        super().__init__()
        self._replacements: Dict[str, str] = dict(replacements)

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
            if token.value in self._replacements:
                token.value = self._replacements[token.value]
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
        self._replacements: Dict[str, str] = dict(replacements)

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
                name_token: str = variable.tokens[2].value
                if name_token in self._replacements:
                    variable.tokens[2].value = self._replacements[name_token]
            except:
                pass
        return self.generic_visit(node)
