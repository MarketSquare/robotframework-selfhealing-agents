from typing import Optional

from bs4 import BeautifulSoup
from robot.libraries.BuiltIn import BuiltIn

from RobotAid.self_healing_system.context_retrieving.dom_utils.dom_soap_utils import SoupDomUtils


class RobotDomUtils:
    """
    A utility class to operate on the DOM of a web page.
    It provides methods to check, extract and manipulate HTML elements.
    """

    def __init__(
        self, library_instance: Optional[object] = None
    ):  # ToDo: Investigate type hint for library_instance
        """
        Initializes the RobotDomUtils class.

        Args:
            library_instance: An instance of the Robot Framework library to interact with.
        """
        self.library_instance = library_instance or BuiltIn().get_library_instance(
            "Browser"
        )

    def is_locator_unique(self, locator: str) -> bool:
        """Checks if the given locator is unique in the DOM.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is unique, False otherwise.
        """
        try:
            return self.library_instance.get_element_count(locator) == 1
        except Exception:
            return False

    def is_locator_visible(self, locator: str) -> bool:
        """Checks if the given locator is visible in the DOM.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is visible, False otherwise.
        """
        return "visible" in self.library_instance.get_element_states(locator)

    def get_dom_tree(self) -> str:
        """
        Retrieves the DOM tree of the current page.

        Returns:
            str: The DOM tree as a string.
        """
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
            shadowdom_exists: bool = self.library_instance.evaluate_javascript(
                None, shadowdom_exist_script
            )
            if shadowdom_exists:
                soup: BeautifulSoup = BeautifulSoup(
                    self.library_instance.evaluate_javascript(None, script),
                    "html.parser",
                )
            else:
                soup: BeautifulSoup = BeautifulSoup(
                    self.library_instance.get_page_source(), "html.parser"
                )
        except:
            soup: BeautifulSoup = BeautifulSoup(
                self.library_instance.get_page_source(), "html.parser"
            )

        source: str = SoupDomUtils().get_simplified_dom_tree(str(soup.body))
        return source
