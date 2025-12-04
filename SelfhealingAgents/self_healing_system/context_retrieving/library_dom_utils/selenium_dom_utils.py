import re
from typing import Dict, Iterable, List

from bs4 import BeautifulSoup, Tag
from robot.libraries.BuiltIn import BuiltIn
from selenium.webdriver.remote.webelement import WebElement

from SelfhealingAgents.self_healing_system.context_retrieving.dom_soap_utils import (
    SoupDomUtils,
)
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import (
    BaseDomUtils,
)
from SelfhealingAgents.utils.logging import log


class SeleniumDomUtils(BaseDomUtils):
    """Selenium library specific DOM utility implementation.

    This class provides DOM interaction methods specific to the Robot Framework
    SeleniumLibrary.

    Attributes:
        _library_instance: Instance of the SeleniumLibrary used for DOM interactions.
    """

    TEXT_INPUT_KEYWORDS = {
        "input text",
        "input password",
        "press keys",
        "press key",
        "textarea should contain",
        "textarea value should be",
        "textfield should contain",
        "textfield value should be",
        "clear text",
    }

    CLICK_KEYWORDS = {
        "click button",
        "click link",
        "click element",
        "click image",
        "click element at coordinates",
        "click",
        "click item",
        "check checkbox",
        "uncheck checkbox",
    }

    SELECT_KEYWORDS = {
        "select options",
        "select options by",
        "list",
        "select",
    }

    def __init__(self):
        """Initialize Selenium DOM utilities."""
        self._library_instance = BuiltIn().get_library_instance("SeleniumLibrary")

    def is_locator_valid(self, locator: str) -> bool:
        """Check if the locator is valid using Selenium library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is valid, False otherwise.
        """
        if self._library_instance is None:
            return True
        try:
            # Use dynamic attribute access to handle different SeleniumLibrary versions
            getattr(self._library_instance, "get_webelement")(locator)
            return True
        except Exception:
            return False

    def is_locator_unique(self, locator: str) -> bool:
        """Check if the locator is unique using Selenium library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is unique, False otherwise.
        """
        if self._library_instance is None:
            return True  # Skip validation if library is not available

        try:
            # Use dynamic attribute access to handle different SeleniumLibrary versions
            elements: List[WebElement] = getattr(
                self._library_instance, "get_webelements"
            )(locator)
            return len(elements) == 1
        except Exception:
            return False

    def get_dom_tree(self) -> str:
        """Retrieve the DOM tree using Selenium library methods.

        Returns:
            str: The DOM tree as a string.
        """
        if self._library_instance is None:
            return "<html><body>SeleniumLibrary not available</body></html>"

        try:
            page_source: str = getattr(self._library_instance, "get_source")()

            soup: BeautifulSoup = BeautifulSoup(page_source, "html.parser")
            source: str = SoupDomUtils().get_simplified_dom_tree(
                str(soup.body) if soup.body else str(soup)
            )
            return source

        except Exception as e:
            return f"<html><body>Error retrieving DOM tree: {str(e)}</body></html>"

    def get_library_type(self) -> str:
        """Get the library type identifier.

        Returns:
            str: The library type identifier.
        """
        return "selenium"

    def is_element_clickable(self, locator: str) -> bool:
        """Check if the element is clickable using Selenium library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the element is clickable, False otherwise.
        """
        if self._library_instance is None:
            return False
        try:
            element: WebElement = getattr(self._library_instance, "get_webelement")(
                locator
            )

            # Get tag name using element property
            tag: str = element.tag_name.lower()

            # Check basic clickable tags
            if tag == "button" or tag == "a" or tag == "select":
                return True
            elif tag == "input":
                # Check input type for clickable input elements
                input_type: str = getattr(self._library_instance, "execute_javascript")(
                    "return arguments[0].type;", "ARGUMENTS", element
                )
                if input_type in [
                    "button",
                    "radio",
                    "checkbox",
                    "search",
                    "reset",
                    "submit",
                ]:
                    return True

            # Check for custom/framework-specific clickable elements
            other_clickable_tags: List[str] = [
                "mat-button",  # Angular Material
                "mat-radio-button",
                "mat-checkbox",
                "md-button",  # Older Angular Material
                "ion-button",  # Ionic
                "vaadin-button",  # Vaadin
                "paper-button",  # Polymer
                "x-button",  # Generic custom button
                "select",
                "textarea",
            ]

            if tag in other_clickable_tags:
                return True

            # Check cursor style as final indicator
            cursor_style: str = getattr(self._library_instance, "execute_javascript")(
                "return window.getComputedStyle(arguments[0]).getPropertyValue('cursor');",
                "ARGUMENTS",
                element,
            )
            if cursor_style == "pointer":
                return True

            return False
        except Exception:
            return False

    @log
    def get_locator_proposals(
        self, failed_locator: str, keyword_name: str
    ) -> List[str]:
        """Get proposals for the given locator.

        Args:
            locator: The locator to get proposals for.

        Returns:
            A list of proposed locators.
        """
        dom_tree: str = self.get_dom_tree()
        soup: BeautifulSoup = BeautifulSoup(dom_tree, "html.parser")

        keyword_key: str = (keyword_name or "").lower()
        heuristic_locators: List[str] = self._generate_semantic_locators(
            soup, failed_locator, keyword_key
        )

        match keyword_name:
            case (
                "Input Text"
                | "Input Password"
                | "Press Keys"
                | "Press Key"
                | "Textarea Should Contain"
                | "Textarea Value Should Be"
                | "Textfield Should Contain"
                | "Textfield Value Should Be"
                | "Clear Text"
            ):
                element_types: List[str] = ["textarea", "input"]
                elements = soup.find_all(element_types)
            case (
                "Click Button"
                | "Click Link"
                | "Click Element"
                | "Click Image"
                | "Click Element At Coordinates"
            ):
                element_types: List[str] = [
                    "a",
                    "button",
                    "checkbox",
                    "link",
                    "input",
                    "label",
                    "li",
                    SoupDomUtils.has_direct_text,
                ]
                elements = soup.find_all(element_types)
            case s if "list" in s.lower():
                element_types: List[str] = ["select"]
                elements = soup.find_all(element_types)
            case c if "checkbox" in c.lower():
                element_types: List[str] = ["input", "button", "checkbox"]
                elements = soup.find_all(element_types)
            case "Get Text" | "Element Text Should Be" | "Element Text Should Not Be":
                element_types: List[str] = [
                    "label",
                    "div",
                    "span",
                    SoupDomUtils.has_direct_text,
                ]
                elements = soup.find_all(element_types)
            case _:
                elements = soup.find_all(True)

        filtered_elements: List[Tag] = [
            elem
            for elem in elements
            if (
                (
                    SoupDomUtils.is_leaf_or_lowest(elem)
                    or SoupDomUtils.has_direct_text(elem)
                )
                and (not SoupDomUtils.has_parent_dialog_without_open(elem))
                and (not SoupDomUtils.has_child_dialog_without_open(elem))
                and (not SoupDomUtils.is_headline(elem))
                and (not SoupDomUtils.is_div_in_li(elem))
                and (not SoupDomUtils.is_p(elem))
            )
        ]

        locators: List = list(heuristic_locators)
        # Generate and display unique selectors
        for elem in filtered_elements:
            try:
                locator: str | None = SeleniumDomUtils._get_locator(elem, soup)
            except Exception:
                locator = None
            if locator:
                locators.append(locator)
        return self._deduplicate(locators)

    def get_locator_metadata(self, locator: str) -> List[Dict]:
        """Get metadata for the given locator.

        Args:
            locator: The locator to get metadata for.

        Returns:
            A list of dictionaries containing metadata about elements matching the locator.
        """
        if self._library_instance is None:
            return []

        try:
            element: WebElement = getattr(self._library_instance, "get_webelement")(
                locator
            )
            metadata_list: List = []

            if element:
                metadata: Dict = {}

                # Properties (retrieved via JavaScript execution for consistency)
                property_list = [
                    "tagName",
                    "childElementCount",
                    "innerText",
                    "type",
                    "value",
                    "name",
                ]
                for property in property_list:
                    try:
                        value = getattr(self._library_instance, "execute_javascript")(
                            f"return arguments[0].{property};", "ARGUMENTS", element
                        )
                        if value:
                            metadata[property] = str(value)
                    except Exception:
                        pass

                # Additional properties with parent/sibling context
                additional_properties = [
                    "parentElement.tagName",
                    "parentElement.innerText",
                    "previousSibling.tagName",
                    "previousSibling.innerText",
                    "nextSibling.tagName",
                    "nextSibling.innerText",
                ]
                for property in additional_properties:
                    try:
                        value = getattr(self._library_instance, "execute_javascript")(
                            f"return arguments[0].{property};", "ARGUMENTS", element
                        )
                        if value:
                            metadata[property] = str(value)
                    except Exception:
                        pass

                # Attributes (retrieved via get_attribute)
                allowed_attributes = [
                    "id",
                    "class",
                    "placeholder",
                    "role",
                    "href",
                    "title",
                ]
                for attribute in allowed_attributes:
                    try:
                        value = element.get_attribute(attribute)
                        if value:
                            metadata[attribute] = str(value)
                    except Exception:
                        pass

                # Element state information
                try:
                    metadata["is_displayed"] = element.is_displayed()
                except Exception:
                    metadata["is_displayed"] = False

                try:
                    metadata["is_enabled"] = element.is_enabled()
                except Exception:
                    metadata["is_enabled"] = False

                try:
                    metadata["is_selected"] = element.is_selected()
                except Exception:
                    metadata["is_selected"] = False

                # Clickable detection (following the pattern from your example)
                try:
                    tag_name = metadata.get("tagName", "").upper()
                    clickable_tags = ["BUTTON", "A", "INPUT", "SELECT"]

                    if tag_name in clickable_tags:
                        metadata["clickable"] = True
                    else:
                        # Check cursor style
                        cursor_clickable = False
                        try:
                            cursor_style = getattr(
                                self._library_instance, "execute_javascript"
                            )(
                                "return window.getComputedStyle(arguments[0]).getPropertyValue('cursor');",
                                "ARGUMENTS",
                                element,
                            )
                            cursor_clickable = cursor_style == "pointer"
                        except Exception:
                            pass

                        # Check for other clickable indicators
                        value_clickable = False
                        try:
                            value = getattr(
                                self._library_instance, "execute_javascript"
                            )("return arguments[0].value;", "ARGUMENTS", element)
                            value_clickable = value in ["on", "off"]
                        except Exception:
                            pass

                        checked_clickable = False
                        try:
                            checked = getattr(
                                self._library_instance, "execute_javascript"
                            )("return arguments[0].checked;", "ARGUMENTS", element)
                            checked_clickable = (
                                checked is not None and str(checked) != ""
                            )
                        except Exception:
                            pass

                        metadata["clickable"] = (
                            cursor_clickable or value_clickable or checked_clickable
                        )
                except Exception:
                    metadata["clickable"] = False

                metadata_list.append(metadata)

            return metadata_list

        except Exception:
            return []

    @staticmethod
    def _get_locator(elem: Tag, soup: BeautifulSoup) -> str | None:
        selector: str = SoupDomUtils.generate_unique_xpath_selector(elem, soup)
        if selector:
            return "xpath:" + selector
        return None

    # --- Internal helpers -------------------------------------------------

    def _generate_semantic_locators(
        self, soup: BeautifulSoup, failed_locator: str, keyword_key: str
    ) -> List[str]:
        hint: str = self._strip_locator_hint(failed_locator)
        locators: List[str] = []

        if hint:
            hint_lower: str = hint.lower()
            tokens: List[str] = self._tokenize(hint_lower)

            if keyword_key in self.TEXT_INPUT_KEYWORDS:
                locators.extend(
                    self._collect_form_field_locators(
                        soup,
                        hint,
                        tokens,
                        ["input", "textarea"],
                        prefix="css=",
                    )
                )

            if keyword_key in self.CLICK_KEYWORDS:
                locators.extend(
                    self._collect_form_field_locators(
                        soup,
                        hint,
                        tokens,
                        [
                            "button",
                            "a",
                            "input",
                            "label",
                            "span",
                            "div",
                            "li",
                        ],
                        prefix="css=",
                    )
                )

            if keyword_key in self.SELECT_KEYWORDS or "select" in keyword_key:
                locators.extend(
                    self._collect_form_field_locators(
                        soup,
                        hint,
                        tokens,
                        ["select"],
                        prefix="css=",
                    )
                )

        chained_hint = self._extract_chained_hint(failed_locator)
        if chained_hint:
            locators.extend(
                self._collect_label_only_locators(
                    soup,
                    chained_hint,
                    self._tokenize(chained_hint.lower()),
                    prefix="css=",
                )
            )

        locators.extend(
            self._collect_class_token_locators(soup, failed_locator, prefix="css=")
        )
        return self._deduplicate(locators)

    def _collect_form_field_locators(
        self,
        soup: BeautifulSoup,
        hint: str,
        tokens: List[str],
        target_tags: List[str],
        *,
        prefix: str,
    ) -> List[str]:
        selectors: List[str] = []
        hint_lower: str = hint.lower()

        selectors.extend(
            self._collect_label_only_locators(soup, hint, tokens, prefix=prefix)
        )

        for elem in soup.find_all(target_tags):
            if self._hint_matches_element(elem, tokens):
                css_selector = SoupDomUtils.generate_unique_css_selector(elem, soup)
                if css_selector:
                    selectors.append(f"{prefix}{css_selector}")

        selectors.extend(
            self._collect_text_based_locators(
                soup,
                hint_lower,
                tokens,
                target_tags,
                prefix,
            )
        )

        return selectors

    def _collect_label_only_locators(
        self,
        soup: BeautifulSoup,
        hint: str,
        tokens: List[str],
        *,
        prefix: str,
    ) -> List[str]:
        selectors: List[str] = []
        for label in soup.find_all("label"):
            label_text: str = self._normalize_text(label.get_text(" "))
            if not label_text:
                continue
            if (
                not self._tokens_in_text(tokens, label_text.lower())
                and hint.lower() not in label_text.lower()
            ):
                continue
            related = self._find_related_input(label, soup)
            if related:
                css_selector = SoupDomUtils.generate_unique_css_selector(related, soup)
                if css_selector:
                    selectors.append(f"{prefix}{css_selector}")
        return selectors

    @staticmethod
    def _find_related_input(label: Tag, soup: BeautifulSoup) -> Tag | None:
        for_attr = label.get("for")
        if for_attr:
            candidate = soup.find(id=for_attr)
            if candidate and candidate.name in ["input", "textarea", "select"]:
                return candidate
        sibling_input = label.find_previous("input")
        if sibling_input:
            return sibling_input
        parent = label.parent
        if parent:
            descendant = parent.find(["input", "textarea", "select"])
            if descendant:
                return descendant
        return None

    def _collect_text_based_locators(
        self,
        soup: BeautifulSoup,
        hint_lower: str,
        tokens: List[str],
        target_tags: List[str],
        prefix: str,
    ) -> List[str]:
        selectors: List[str] = []
        for elem in soup.find_all(target_tags):
            text_value: str = self._normalize_text(elem.get_text(" "))
            if not text_value:
                continue
            if hint_lower in text_value.lower() or self._tokens_in_text(
                tokens, text_value.lower()
            ):
                css_selector = SoupDomUtils.generate_unique_css_selector(elem, soup)
                if css_selector:
                    selectors.append(f"{prefix}{css_selector}")
        return selectors

    def _collect_class_token_locators(
        self, soup: BeautifulSoup, failed_locator: str, *, prefix: str
    ) -> List[str]:
        tokens: List[str] = re.findall(r"[a-zA-Z0-9_-]{4,}", failed_locator or "")
        selectors: List[str] = []
        if not tokens:
            return selectors

        for token in dict.fromkeys(token.lower() for token in tokens):
            match = soup.find(
                lambda tag: any(
                    token in value.lower()
                    for attr in ("id", "class", "name", "role", "type")
                    for value in (
                        tag.get(attr)
                        if isinstance(tag.get(attr), list)
                        else [tag.get(attr)]
                        if tag.get(attr)
                        else []
                    )
                )
            )
            if match:
                css_selector = SoupDomUtils.generate_unique_css_selector(match, soup)
                if css_selector:
                    selectors.append(f"{prefix}{css_selector}")
        return selectors

    @staticmethod
    def _strip_locator_hint(value: str | None) -> str:
        if not value:
            return ""
        hint = value.strip()
        if hint.startswith(("'", '"')) and hint.endswith(("'", '"')):
            hint = hint[1:-1]
        return hint.strip()

    @staticmethod
    def _extract_chained_hint(value: str | None) -> str:
        if not value or ">>" not in value:
            return ""
        chained = value.split(">>")[-1].strip()
        if chained.startswith(("'", '"')) and chained.endswith(("'", '"')):
            chained = chained[1:-1]
        return chained.strip()

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        if not value:
            return ""
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _tokenize(value: str) -> List[str]:
        return [token for token in re.split(r"\s+", value) if len(token) >= 3]

    def _hint_matches_element(self, elem: Tag, tokens: List[str]) -> bool:
        for attr in ("id", "name", "placeholder", "value", "role", "type"):
            attr_val = elem.get(attr)
            if isinstance(attr_val, str) and self._tokens_in_text(
                tokens, attr_val.lower()
            ):
                return True
        class_attr = elem.get("class")
        if class_attr and any(
            self._tokens_in_text(tokens, cls.lower()) for cls in class_attr
        ):
            return True
        return False

    @staticmethod
    def _tokens_in_text(tokens: Iterable[str], text_value: str) -> bool:
        return any(token in text_value for token in tokens)

    @staticmethod
    def _deduplicate(locators: List[str]) -> List[str]:
        unique: List[str] = []
        seen: set[str] = set()
        for locator in locators:
            if not locator or locator in seen:
                continue
            seen.add(locator)
            unique.append(locator)
        return unique
