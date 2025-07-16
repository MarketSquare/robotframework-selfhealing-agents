from typing import Optional

from bs4 import BeautifulSoup
from robot.libraries.BuiltIn import BuiltIn

from RobotAid.self_healing_system.context_retrieving.base_dom_utils import BaseDomUtils
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
                    locator, f"(elem) => elem.{'control.type'}"
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
