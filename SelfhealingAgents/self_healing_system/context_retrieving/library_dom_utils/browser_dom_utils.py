import re
from typing import Callable, Dict, Iterable, List

from bs4 import BeautifulSoup, ResultSet, Tag
from robot.libraries.BuiltIn import BuiltIn

from SelfhealingAgents.self_healing_system.context_retrieving.dom_soap_utils import (
    SoupDomUtils,
)
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import (
    BaseDomUtils,
)
from SelfhealingAgents.utils.logging import log


class BrowserDomUtils(BaseDomUtils):
    """Browser library specific DOM utility implementation.

    This class provides DOM interaction methods specific to the Robot Framework
    Browser library (Playwright-based).

    Attributes:
        _library_instance: Instance of the Browser library used for DOM interactions.
    """

    TEXT_INPUT_KEYWORDS = {
        "fill text",
        "type text",
        "press keys",
        "fill secret",
        "type secret",
        "clear text",
    }

    CLICK_KEYWORDS = {
        "click",
        "click with options",
        "click button",
        "click link",
        "click element",
        "click image",
        "click element at coordinates",
        "check checkbox",
        "uncheck checkbox",
    }

    SELECT_KEYWORDS = {
        "select options by",
        "deselect options",
        "select",
        "select options",
    }

    def __init__(self):
        """Initialize Browser DOM utilities."""
        self._library_instance = BuiltIn().get_library_instance("Browser")

    def is_locator_valid(self, locator: str) -> bool:
        """Check if the given locator is valid using Browser library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is valid, False otherwise.
        """
        if self._library_instance is None:
            return True
        try:
            # Use dynamic attribute access to handle different Browser library versions
            elements: List[str] = getattr(self._library_instance, "get_elements")(
                locator
            )
            return len(elements) > 0
        except Exception:
            return False

    def is_locator_unique(self, locator: str) -> bool:
        """Check if the given locator is unique using Browser library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is unique, False otherwise.
        """
        if self._library_instance is None:
            return True  # Skip validation if library is not available

        try:
            return getattr(self._library_instance, "get_element_count")(locator) == 1
        except Exception:
            return False

    def get_dom_tree(self) -> str:
        """Retrieve the DOM tree using Browser library methods.

        Returns:
            str: The DOM tree as a string.
        """
        if self._library_instance is None:
            return "<html><body>Browser library not available</body></html>"

        script: str = """() =>
        {
        function getFullInnerHTML(node = document.documentElement) {
            // Function to process each node and retrieve its HTML including Shadow DOM
            function processNode(node) {
                let html = "";

                // Check if the node is an element
                if (node.nodeType === Node.ELEMENT_NODE) {
                    // If the node has a Shadow DOM, recursively process its shadow DOM
                    if (node.shadowRoot) {
                        html += `<${node.tagName.toLowerCase()}${getAttributes(node)}>`;
                        html += processNode(node.shadowRoot);
                        html += `</${node.tagName.toLowerCase()}>`;
                    } else {
                        // Process children if no Shadow DOM is present
                        html += `<${node.tagName.toLowerCase()}${getAttributes(node)}>`;
                        for (let child of node.childNodes) {
                            html += processNode(child);
                        }
                        html += `</${node.tagName.toLowerCase()}>`;
                    }
                } else if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
                    // Process ShadowRoot (document fragments)
                    for (let child of node.childNodes) {
                        html += processNode(child);
                    }
                } else if (node.nodeType === Node.TEXT_NODE) {
                    // Add text content for text nodes
                    html += node.textContent;
                }
                return html;
            }

            // Helper function to get attributes of an element
            function getAttributes(node) {
                if (node.attributes && node.attributes.length > 0) {
                    return Array.from(node.attributes)
                        .map(attr => ` ${attr.name}="${attr.value}"`)
                        .join("");
                }
                return "";
            }

            // Start processing from the root node
            return processNode(node);
        }

        // Get the full inner HTML including all Shadow DOMs
        const fullHTML = getFullInnerHTML();
        return fullHTML;
            }
        """

        shadowdom_exist_script: str = """ () => {      
        return Array.from(document.querySelectorAll('*')).some(el => el.shadowRoot);
        }
        """

        try:
            shadowdom_exists: bool = getattr(
                self._library_instance, "evaluate_javascript"
            )(None, shadowdom_exist_script)
            if shadowdom_exists:
                soup: BeautifulSoup = BeautifulSoup(
                    getattr(self._library_instance, "evaluate_javascript")(
                        None, script
                    ),
                    "html.parser",
                )
            else:
                soup: BeautifulSoup = BeautifulSoup(
                    getattr(self._library_instance, "get_page_source")(), "html.parser"
                )
        except Exception:
            try:
                soup: BeautifulSoup = BeautifulSoup(
                    getattr(self._library_instance, "get_page_source")(), "html.parser"
                )
            except Exception:
                return "<html><body>Unable to retrieve DOM tree</body></html>"

        source: str = SoupDomUtils().get_simplified_dom_tree(
            str(soup.body) if soup.body else str(soup)
        )
        return source

    def get_library_type(self) -> str:
        """Get the library type identifier.

        Returns:
            str: The library type identifier.
        """
        return "browser"

    def is_element_clickable(self, locator: str) -> bool | None:
        """Check if the element identified by the locator is clickable using Browser library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the element is clickable, False otherwise.
        """
        # clickable_tags = ["button", "a", "input", "select", "textarea"]
        if self._library_instance is None:
            return False
        try:
            element: str = getattr(self._library_instance, "get_element")(locator)
            # Use get_property_value to check the tagName
            tag: str = getattr(self._library_instance, "get_property")(
                element, "tagName"
            ).lower()

            if tag == "button" or tag == "a" or tag == "select":
                return True
            elif tag == "input":
                type: str = getattr(self._library_instance, "evaluate_javascript")(
                    locator, f"(elem) => elem.{'type'}"
                )
                if (
                    type == "button"
                    or type == "radio"
                    or type == "checkbox"
                    or type == "search"
                    or type == "reset"
                    or type == "submit"
                ):
                    return True

            other_clickable_tags: List[str] = [
                "mat-button",  # Angular Material
                "mat-radio-button",
                "mat-checkbox",
                "md-button",  # Older Angular Material
                "ion-button",  # Ionic
                "vaadin-button",  # Vaadin
                "paper-button",  # Polymer
                "x-button",  # Generic custom button
            ]

            if tag in other_clickable_tags:
                return True

            cursor_style: str = getattr(self._library_instance, "get_style")(
                locator, "cursor"
            )
            if cursor_style == "pointer":
                return True

        except Exception:
            return False

    @log
    def get_locator_proposals(
        self, failed_locator: str, keyword_name: str
    ) -> list[str]:
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

        elements: ResultSet = soup.find_all(True)

        match keyword_name:
            case (
                "Fill Text"
                | "Type Text"
                | "Press Keys"
                | "Fill Secret"
                | "Type Secret"
                | "Clear Text"
            ):
                element_types: List[str] = ["textarea", "input"]
                elements = soup.find_all(element_types)
            case "Click" | "Click With Options":
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
            case "Select Options By" | "Deselect Options":
                element_types: List[str] = ["select"]
                elements = soup.find_all(element_types)
            case "Check Checkbox" | "Uncheck Checkbox":
                element_types: List[str] = ["input", "button", "checkbox"]
                elements = soup.find_all(element_types)
            case "Get Text":
                element_types: List[str] = [
                    "label",
                    "div",
                    "span",
                    SoupDomUtils.has_direct_text,
                ]
                elements = soup.find_all(element_types)

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
                locator: str | None = BrowserDomUtils._get_locator(elem, soup)
            except Exception:
                locator = None
            if locator:
                locators.append(locator)
        return self._deduplicate(locators)

    def get_locator_metadata(self, locator: str) -> list[dict]:
        """Get metadata for the given locator.

        Args:
            locator: The locator to get metadata for.

        Returns:
            A list of dictionaries containing metadata about elements matching the locator.
        """
        if self._library_instance is None:
            return []

        try:
            elements: List[str] = getattr(self._library_instance, "get_elements")(
                locator
            )
            metadata_list: List = []

            for element in elements:
                metadata: Dict = {}

                # Properties (retrieved via evaluate_javascript)
                property_list: List[str] = [
                    "tagName",
                    "childElementCount",
                    "innerText",
                    "type",
                    "value",
                    "name",
                ]
                for property in property_list:
                    try:
                        value: str = getattr(
                            self._library_instance, "evaluate_javascript"
                        )(element, f"(elem) => elem.{property}")
                        if value:
                            metadata[property] = str(value)
                    except Exception:
                        pass

                # Additional properties with parent/sibling context
                additional_properties: List[str] = [
                    "parentElement.tagName",
                    "parentElement.innerText",
                    "previousSibling.tagName",
                    "previousSibling.innerText",
                    "nextSibling.tagName",
                    "nextSibling.innerText",
                ]
                for property in additional_properties:
                    try:
                        value: str = getattr(
                            self._library_instance, "evaluate_javascript"
                        )(element, f"(elem) => elem.{property}")
                        if value:
                            metadata[property] = str(value)
                    except Exception:
                        pass

                # Attributes (retrieved via get_attribute)
                allowed_attributes: List[str] = [
                    "id",
                    "class",
                    "placeholder",
                    "role",
                    "href",
                    "title",
                ]
                try:
                    attribute_list: List[str] = getattr(
                        self._library_instance, "get_attribute_names"
                    )(element)
                    for attribute in allowed_attributes:
                        if attribute in attribute_list:
                            try:
                                value: str = getattr(
                                    self._library_instance, "get_attribute"
                                )(element, attribute)
                                if value:
                                    metadata[attribute] = str(value)
                            except Exception:
                                pass
                except Exception:
                    # Fallback: try to get common attributes directly
                    for attribute in allowed_attributes:
                        try:
                            value: str = getattr(
                                self._library_instance, "get_attribute"
                            )(element, attribute)
                            if value:
                                metadata[attribute] = str(value)
                        except Exception:
                            pass

                # Element state information using Browser library methods
                try:
                    metadata["is_visible"] = "visible" in getattr(
                        self._library_instance, "get_element_states"
                    )(element)
                except Exception:
                    metadata["is_visible"] = False

                try:
                    metadata["is_enabled"] = "enabled" in getattr(
                        self._library_instance, "get_element_states"
                    )(element)
                except Exception:
                    metadata["is_enabled"] = False

                try:
                    metadata["is_checked"] = "checked" in getattr(
                        self._library_instance, "get_element_states"
                    )(element)
                except Exception:
                    metadata["is_checked"] = False

                metadata_list.append(metadata)

            return metadata_list

        except Exception:
            return []

    @staticmethod
    def _get_locator(elem: Tag, soup: BeautifulSoup) -> str | None:
        """Generates a unique CSS locator string for the given element.

        Attempts to generate a unique CSS selector for the provided BeautifulSoup Tag
        within the given soup. If a unique selector is found, returns it as a string
        prefixed with 'css='. Otherwise, returns None.

        Args:
            elem (Tag): The BeautifulSoup Tag element for which to generate the locator.
            soup (BeautifulSoup): The BeautifulSoup object representing the DOM.

        Returns:
            str | None: The unique CSS locator string prefixed with 'css=', or None if not found.
        """
        selector: str = SoupDomUtils.generate_unique_css_selector(elem, soup)
        if selector:
            return "css=" + selector
        # else:
        #     selector = generate_unique_xpath_selector(elem, soup)
        #     if selector:
        #         return "xpath=" + selector
        return None

    # --- Internal helpers -------------------------------------------------

    def _generate_semantic_locators(
        self, soup: BeautifulSoup, failed_locator: str, keyword_key: str
    ) -> List[str]:
        hint: str = self._strip_locator_hint(failed_locator)
        locators: List[str] = []
        if not hint:
            locators.extend(
                self._collect_class_token_locators(soup, failed_locator, prefix="css=")
            )
            return locators

        hint_lower: str = hint.lower()
        tokens: List[str] = self._tokenize(hint_lower)

        if keyword_key in self.TEXT_INPUT_KEYWORDS:
            locators.extend(
                self._collect_form_field_locators(
                    soup,
                    hint,
                    tokens,
                    target_tags=["input", "textarea"],
                    prefix="css=",
                )
            )

        if keyword_key in self.CLICK_KEYWORDS:
            locators.extend(
                self._collect_form_field_locators(
                    soup,
                    hint,
                    tokens,
                    target_tags=[
                        "button",
                        "a",
                        "mat-radio-button",
                        "mat-checkbox",
                        "mat-button",
                        "label",
                        "li",
                        "div",
                        "span",
                    ],
                    prefix="css=",
                )
            )

        if keyword_key in self.SELECT_KEYWORDS:
            locators.extend(
                self._collect_form_field_locators(
                    soup,
                    hint,
                    tokens,
                    target_tags=["select", "mat-select"],
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
        *,
        target_tags: List[str],
        prefix: str,
    ) -> List[str]:
        selectors: List[str] = []
        hint_lower: str = hint.lower()

        # Label based suggestions
        for label in soup.find_all("label"):
            label_text: str = self._normalize_text(label.get_text(" "))
            if not label_text:
                continue
            if self._tokens_in_text(tokens, label_text.lower()):
                for_attr = label.get("for")
                if for_attr:
                    selectors.append(f"{prefix}#{for_attr}")
                    selectors.append(f"{prefix}input#{for_attr}")
                nested = label.find(["input", "textarea", "select"])
                if nested:
                    css_selector = SoupDomUtils.generate_unique_css_selector(
                        nested, soup
                    )
                    if css_selector:
                        selectors.append(f"{prefix}{css_selector}")

        # Attribute matches on the target tags
        for elem in soup.find_all(target_tags):
            if self._hint_matches_element(elem, tokens):
                css_selector = SoupDomUtils.generate_unique_css_selector(elem, soup)
                if css_selector:
                    selectors.append(f"{prefix}{css_selector}")

        # Text-based match for clickable elements
        if target_tags != ["input", "textarea"]:
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

        def token_predicate(token: str) -> Callable[[Tag], bool]:
            lowered = token.lower()

            def _matcher(tag: Tag) -> bool:
                for attr in ("id", "class", "name", "role", "type"):
                    value = tag.get(attr)
                    if isinstance(value, list) and any(
                        lowered in entry.lower() for entry in value
                    ):
                        return True
                    if isinstance(value, str) and lowered in value.lower():
                        return True
                return False

            return _matcher

        seen_tokens: set[str] = set()
        for token in tokens:
            token_lower = token.lower()
            if token_lower in seen_tokens:
                continue
            seen_tokens.add(token_lower)
            match = soup.find(token_predicate(token_lower))
            if not match:
                continue
            css_selector = SoupDomUtils.generate_unique_css_selector(match, soup)
            if css_selector:
                selectors.append(f"{prefix}{css_selector}")
        return selectors

    @staticmethod
    def _strip_locator_hint(value: str | None) -> str:
        if not value:
            return ""
        hint = value.strip()
        if " >> " in hint:
            hint = hint.split(">>")[-1].strip()
        if hint.startswith(("'", '"')) and hint.endswith(("'", '"')):
            hint = hint[1:-1]
        return hint.strip()

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        if not value:
            return ""
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _tokenize(hint_lower: str) -> List[str]:
        return [token for token in re.split(r"\s+", hint_lower) if len(token) >= 3]

    def _hint_matches_element(self, elem: Tag, tokens: List[str]) -> bool:
        for attr in ("id", "name", "placeholder", "value", "role", "type"):
            value = elem.get(attr)
            if isinstance(value, str) and self._tokens_in_text(tokens, value.lower()):
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
