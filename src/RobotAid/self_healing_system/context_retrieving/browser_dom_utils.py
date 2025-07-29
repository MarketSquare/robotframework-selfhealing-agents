from typing import Optional

from bs4 import BeautifulSoup
from robot.libraries.BuiltIn import BuiltIn

from RobotAid.self_healing_system.context_retrieving.base_dom_utils import (
    BaseDomUtils,
    generate_unique_css_selector,
    has_child_dialog_without_open,
    has_direct_text,
    has_parent_dialog_without_open,
    is_div_in_li,
    is_headline,
    is_leaf_or_lowest,
    is_p,
)
from RobotAid.self_healing_system.context_retrieving.dom_soap_utils import SoupDomUtils


class BrowserDomUtils(BaseDomUtils):
    """Browser library specific DOM utility implementation.

    This class provides DOM interaction methods specific to the Robot Framework
    Browser library (Playwright-based).
    """

    def __init__(self, library_instance: Optional[object] = None):
        """Initialize Browser DOM utilities.

        Args:
            library_instance: An instance of the Browser library.
        """
        if library_instance is None:
            try:
                library_instance = BuiltIn().get_library_instance("Browser")
            except Exception:
                print(
                    "Browser library is not available. Browser DOM utility will be limited."
                )
                library_instance = None

        super().__init__(library_instance)

    def is_locator_valid(self, locator: str) -> bool:
        """Check if the given locator is valid using Browser library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is valid, False otherwise.
        """
        if self.library_instance is None:
            return True
        try:
            # Use dynamic attribute access to handle different Browser library versions
            elements = getattr(self.library_instance, "get_elements")(locator)
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
        if self.library_instance is None:
            return True  # Skip validation if library is not available

        try:
            return getattr(self.library_instance, "get_element_count")(locator) == 1
        except Exception:
            return False

    def is_locator_visible(self, locator: str) -> bool:
        """Check if the given locator is visible using Browser library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is visible, False otherwise.
        """
        if self.library_instance is None:
            return True  # Skip validation if library is not available

        try:
            return "visible" in getattr(self.library_instance, "get_element_states")(
                locator
            )
        except Exception:
            return False

    def get_dom_tree(self) -> str:
        """Retrieve the DOM tree using Browser library methods.

        Returns:
            str: The DOM tree as a string.
        """
        if self.library_instance is None:
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
                self.library_instance, "evaluate_javascript"
            )(None, shadowdom_exist_script)
            if shadowdom_exists:
                soup: BeautifulSoup = BeautifulSoup(
                    getattr(self.library_instance, "evaluate_javascript")(None, script),
                    "html.parser",
                )
            else:
                soup: BeautifulSoup = BeautifulSoup(
                    getattr(self.library_instance, "get_page_source")(), "html.parser"
                )
        except Exception:
            try:
                soup: BeautifulSoup = BeautifulSoup(
                    getattr(self.library_instance, "get_page_source")(), "html.parser"
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

    def is_element_clickable(self, locator: str) -> bool:
        """Check if the element identified by the locator is clickable using Browser library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the element is clickable, False otherwise.
        """
        # clickable_tags = ["button", "a", "input", "select", "textarea"]
        if self.library_instance is None:
            return False
        try:
            element = getattr(self.library_instance, "get_element")(locator)
            # Use get_property_value to check the tagName
            tag = getattr(self.library_instance, "get_property")(
                element, "tagName"
            ).lower()

            if tag == "button" or tag == "a" or tag == "select":
                return True
            elif tag == "input":
                type = getattr(self.library_instance, "evaluate_javascript")(
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

            other_clickable_tags = [
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

            cursor_style = getattr(self.library_instance, "get_style")(
                locator, "cursor"
            )
            if cursor_style == "pointer":
                return True

        except Exception:
            return False

    def get_locator_proposals(
        self, failed_locator: str, keyword_name: str
    ) -> list[str]:
        """Get proposals for the given locator.

        Args:
            locator: The locator to get proposals for.

        Returns:
            A list of proposed locators.
        """
        dom_tree = self.get_dom_tree()
        soup = BeautifulSoup(dom_tree, "html.parser")

        match keyword_name:
            case (
                "Fill Text"
                | "Type Text"
                | "Press Keys"
                | "Fill Secret"
                | "Type Secret"
                | "Clear Text"
            ):
                element_types = ["textarea", "input"]
                elements = soup.find_all(element_types)
            case "Click" | "Click With Options":
                element_types = [
                    "a",
                    "button",
                    "checkbox",
                    "link",
                    "input",
                    "label",
                    "li",
                    has_direct_text,
                ]
                elements = soup.find_all(element_types)
            case "Select Options By" | "Deselect Options":
                element_types = ["select"]
                elements = soup.find_all(element_types)
            case "Check Checkbox" | "Uncheck Checkbox":
                element_types = ["input", "button", "checkbox"]
                elements = soup.find_all(element_types)
            case "Get Text":
                element_types = ["label", "div", "span", has_direct_text]
                elements = soup.find_all(element_types)

        filtered_elements = [
            elem
            for elem in elements
            if (
                (is_leaf_or_lowest(elem) or has_direct_text(elem))
                and (not has_parent_dialog_without_open(elem))
                and (not has_child_dialog_without_open(elem))
                and (not is_headline(elem))
                and (not is_div_in_li(elem))
                and (not is_p(elem))
            )
        ]

        locators = []
        # Generate and display unique selectors
        for elem in filtered_elements:
            try:
                locator = get_locator(elem, soup)
            except Exception:
                locator = None
            if locator:
                locators.append(locator)
        return locators

    def get_locator_metadata(self, locator: str) -> list[dict]:
        """Get metadata for the given locator.

        Args:
            locator: The locator to get metadata for.

        Returns:
            A list of dictionaries containing metadata about elements matching the locator.
        """
        if self.library_instance is None:
            return []

        try:
            elements = getattr(self.library_instance, "get_elements")(locator)
            metadata_list = []

            for element in elements:
                metadata = {}

                # Properties (retrieved via evaluate_javascript)
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
                        value = getattr(self.library_instance, "evaluate_javascript")(
                            element, f"(elem) => elem.{property}"
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
                        value = getattr(self.library_instance, "evaluate_javascript")(
                            element, f"(elem) => elem.{property}"
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
                try:
                    attribute_list = getattr(
                        self.library_instance, "get_attribute_names"
                    )(element)
                    for attribute in allowed_attributes:
                        if attribute in attribute_list:
                            try:
                                value = getattr(self.library_instance, "get_attribute")(
                                    element, attribute
                                )
                                if value:
                                    metadata[attribute] = str(value)
                            except Exception:
                                pass
                except Exception:
                    # Fallback: try to get common attributes directly
                    for attribute in allowed_attributes:
                        try:
                            value = getattr(self.library_instance, "get_attribute")(
                                element, attribute
                            )
                            if value:
                                metadata[attribute] = str(value)
                        except Exception:
                            pass

                # Element state information using Browser library methods
                try:
                    metadata["is_visible"] = "visible" in getattr(
                        self.library_instance, "get_element_states"
                    )(element)
                except Exception:
                    metadata["is_visible"] = False

                try:
                    metadata["is_enabled"] = "enabled" in getattr(
                        self.library_instance, "get_element_states"
                    )(element)
                except Exception:
                    metadata["is_enabled"] = False

                try:
                    metadata["is_checked"] = "checked" in getattr(
                        self.library_instance, "get_element_states"
                    )(element)
                except Exception:
                    metadata["is_checked"] = False

                metadata_list.append(metadata)

            return metadata_list

        except Exception:
            return []


def get_locator(elem, soup):
    selector = generate_unique_css_selector(elem, soup)
    if selector:
        return "css=" + selector
    # else:
    #     selector = generate_unique_xpath_selector(elem, soup)
    #     if selector:
    #         return "xpath=" + selector
    return None
