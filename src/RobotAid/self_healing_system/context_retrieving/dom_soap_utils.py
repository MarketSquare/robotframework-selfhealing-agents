import re
from typing import List
from lxml import etree
from bs4 import BeautifulSoup, Tag, ResultSet

from RobotAid.utils.logging import log


class SoupDomUtils:
    """Utility class for operating on the DOM of a web page using BeautifulSoup."""
    @staticmethod
    def clean_text_for_selector(text: str) -> str:
        """Sanitizes text for use in a CSS selector.

        Removes leading/trailing whitespace and collapses internal whitespace to a single space.

        Args:
            text (str): The text to sanitize.

        Returns:
            str: The sanitized text suitable for use in a CSS selector.
        """
        return re.sub(r"\s+", " ", text.strip())

    @staticmethod
    def get_selector_count(soup: BeautifulSoup, selector: str) -> int:
        """Returns the number of elements matching a CSS selector.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object representing the DOM.
            selector (str): The CSS selector to match.

        Returns:
            int: The number of elements matching the selector, or 0 if an error occurs.
        """
        try:
            elements: ResultSet = soup.select(selector)
            return len(elements)
        except Exception:
            return 0

    @staticmethod
    def is_selector_unique(soup: BeautifulSoup, selector: str) -> bool:
        """Checks if the CSS selector matches exactly one element.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object representing the DOM.
            selector (str): The CSS selector to check.

        Returns:
            bool: True if exactly one element matches the selector, False otherwise.
        """
        try:
            elements: ResultSet = soup.select(selector)
            return len(elements) == 1
        except Exception:
            return False

    @staticmethod
    def has_child_dialog_without_open(element: Tag) -> bool:
        """Checks if any child of the given element is a <dialog> without the 'open' attribute.

        Args:
            element (Tag): The BeautifulSoup Tag to check.

        Returns:
            bool: True if a child <dialog> exists without the 'open' attribute, False otherwise.
        """
        try:
            dialog: List[Tag] = [
                x for x in element.children if isinstance(x, Tag) and x.name == "dialog"
            ]
            for d in dialog:
                if not d.has_attr("open"):
                    return True
            return False
        except Exception:
            return True

    @staticmethod
    def is_headline(tag: Tag) -> bool:
        """Checks if the tag is a headline element (h1-h6).

        Args:
            tag (Tag): The BeautifulSoup Tag to check.

        Returns:
            bool: True if the tag is a headline element, False otherwise.
        """
        return tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]

    @staticmethod
    def is_div_in_li(tag: Tag) -> bool:
        """Checks if the tag is a <div> inside a <li> element.

        Args:
            tag (Tag): The BeautifulSoup Tag to check.

        Returns:
            bool: True if the tag is a <div> within a <li>, False otherwise.
        """
        if tag.name != "div":
            return False

        parent: Tag | None = tag.find_parent("li")
        return parent is not None

    @staticmethod
    def is_p(tag: Tag) -> bool:
        """Checks if the tag is a <p> (paragraph) element.

        Args:
            tag (Tag): The BeautifulSoup Tag to check.

        Returns:
            bool: True if the tag is a <p> element, False otherwise.
        """
        if tag.name == "p":
            return True
        else:
            return False

    @staticmethod
    def has_parent_dialog_without_open(element: Tag) -> bool:
        """Checks if any parent of the given element is a <dialog> without the 'open' attribute.

        Args:
            element (Tag): The BeautifulSoup Tag to check.

        Returns:
            bool: True if a parent <dialog> exists without the 'open' attribute, False otherwise.
        """
        try:
            dialog: List[Tag] = [
                x for x in element.parents if isinstance(x, Tag) and x.name == "dialog"
            ]
            for d in dialog:
                if not d.has_attr("open"):
                    return True
            return False
        except Exception:
            return True

    @staticmethod
    def is_leaf_or_lowest(element: Tag) -> bool:
        """Checks if the element is a leaf or the lowest of its type in the DOM branch.

        An element is considered a leaf if it has no child elements. It is considered
        the lowest of its type if there are no descendants of the same tag name.

        Args:
            element (Tag): The BeautifulSoup Tag to check.

        Returns:
            bool: True if the element is a leaf or the lowest of its type, False otherwise.
        """
        # Check if the element has no child elements (leaf)
        if not element.find():
            return True

        # Check if the element is the lowest of its type in this branch
        tag_name: str = element.name
        if not element.find_all(tag_name):
            return True

        return False

    @staticmethod
    def has_direct_text(tag: Tag) -> bool:
        """Checks if the tag has any direct text (not in its children).

        Args:
            tag (Tag): The BeautifulSoup Tag to check.

        Returns:
            bool: True if the tag has direct text and no child elements, False otherwise.
        """
        # Check if the tag has any direct text (not in its children)
        return tag.string is not None and tag.string.strip() and not tag.find()

    @staticmethod
    @log
    def generate_unique_css_selector(
        element: Tag,
        soup: BeautifulSoup,
        *,
        check_parents: bool = True,
        check_siblings: bool = True,
        check_children: bool = True,
        check_text: bool = True,
        only_return_unique_selectors: bool = True,
        text_exclusions: List[str] | None = None,
    ) -> str | None:
        """Generates a unique CSS selector for the given element within the soup.

        Attempts to build a selector using tag name, attributes, text content, and
        relationships to parents and siblings. Returns the selector if it uniquely
        identifies the element in the DOM.

        Args:
            element (Tag): The BeautifulSoup Tag for which to generate the selector.
            soup (BeautifulSoup): The BeautifulSoup object representing the DOM.
            check_parents (bool): Whether to include parent relationships in the selector.
            check_siblings (bool): Whether to include sibling relationships in the selector.
            check_children (bool): Whether to include child relationships in the selector.
            check_text (bool): Whether to include text content in the selector.
            only_return_unique_selectors (bool): If True, only return selectors that are unique.
            text_exclusions (List[str] | None): List of text strings to exclude from selector generation.

        Returns:
            str | None: A unique CSS selector string if found, otherwise None.
        """
        steps: List[str] = []
        text_steps: List[str] = []

        element_contains_text: bool = False
        if text_exclusions is None:
            text_exclusions = []

        tag_selector: str = f"{element.name}"
        steps.append(tag_selector)

        # Step 2: ID
        if element.get("id"):
            id_selector: str = f"#{element['id']}"
            if SoupDomUtils.is_selector_unique(soup, f"{element.name}{id_selector}"):
                return f"{element.name}{id_selector}"
            steps.append(id_selector)

        if element.get("name"):
            name_selector: str = f'[name="{element["name"]}"]'
            if SoupDomUtils.is_selector_unique(soup, f"{element.name}{name_selector}"):
                return f"{element.name}{name_selector}"
            steps.append(name_selector)

        if element.get("type"):
            type_selector: str = f'[type="{element["type"]}"]'
            if SoupDomUtils.is_selector_unique(soup, f"{element.name}{type_selector}"):
                return f"{element.name}{type_selector}"
            steps.append(type_selector)

        if element.get("placeholder"):
            placeholder_selector: str = f'[placeholder="{element["placeholder"]}"]'
            if SoupDomUtils.is_selector_unique(
                soup, f"{element.name}{placeholder_selector}"
            ):
                return f"{element.name}{placeholder_selector}"
            steps.append(placeholder_selector)

        if element.get("role"):
            role_selector: str = f'[role="{element["role"]}"]'
            if SoupDomUtils.is_selector_unique(soup, f"{element.name}{role_selector}"):
                return f"{element.name}{role_selector}"
            steps.append(role_selector)

        if element.get("class"):
            filtered_classes: List[str] = [x for x in element["class"] if "hidden" not in x]
            class_list: List[str] = []
            class_selector: str | None = None
            for single_class in filtered_classes:
                class_list.append(single_class)
                class_selector = "." + ".".join(class_list)
                if SoupDomUtils.is_selector_unique(
                    soup, f"{element.name}{class_selector}"
                ):
                    return f"{element.name}{class_selector}"
            if class_selector:
                steps.append(class_selector)

        if check_text:
            text_selectors: List[str] = []
            selector_count: int = 0
            # Step 4: Text Content
            if element.text.strip():
                element_contains_text = True
                if element.string and element.string not in text_exclusions:
                    sanitized_text: str = SoupDomUtils.clean_text_for_selector(
                        element.string
                    )
                    text_selector: str = f':-soup-contains-own("{sanitized_text}")'
                    selector_count = SoupDomUtils.get_selector_count(
                        soup, f"{''.join(steps)}{text_selector}"
                    )
                    if selector_count == 1:
                        return f"{''.join(steps)}{text_selector}"
                    elif selector_count > 1:
                        text_steps.append(text_selector)
                if not element.string or selector_count == 0:
                    for text in element.stripped_strings:
                        if text not in text_exclusions:
                            sanitized_text = SoupDomUtils.clean_text_for_selector(text)
                            text_selector = f':-soup-contains("{sanitized_text}")'
                            text_selectors.append(text_selector)

                            selector_count = SoupDomUtils.get_selector_count(
                                soup, f"{''.join(steps)}{''.join(text_selectors)}"
                            )
                            if selector_count == 1:
                                return f"{''.join(steps)}{''.join(text_selectors)}"
                            elif selector_count > 1:
                                text_steps.append(text_selector)
                            elif selector_count == 0:
                                break

        # Special check for items inside li/ul
        if element.find_parent("li"):
            if element.find_parent("ul"):
                ul_parent_selector: str | None = SoupDomUtils.generate_unique_css_selector(
                    element.find_parent("ul"),
                    soup,
                    check_parents=True,
                    check_siblings=False,
                    check_text=False,
                    only_return_unique_selectors=False,
                )
                li_parent_selector: str | None = SoupDomUtils.generate_unique_css_selector(
                    element.find_parent("li"),
                    soup,
                    check_parents=False,
                    check_siblings=False,
                    check_text=False,
                    only_return_unique_selectors=False,
                )
                ul_li_selector: str = (
                    f"{ul_parent_selector} > {li_parent_selector} {''.join(steps)}"
                )
                if SoupDomUtils.is_selector_unique(soup, ul_li_selector):
                    return ul_li_selector
        elif element.find_parent("ul"):
            ul_parent_selector = SoupDomUtils.generate_unique_css_selector(
                element.find_parent("ul"),
                soup,
                check_parents=True,
                check_siblings=False,
                check_text=False,
                only_return_unique_selectors=False,
            )
            ul_selector: str = f"{ul_parent_selector} > {''.join(steps)}"
            if SoupDomUtils.is_selector_unique(soup, ul_selector):
                return ul_selector

        if check_siblings:
            # Step 7: Sibling Relationships
            siblings: ResultSet = element.find_previous_siblings()
            for sibling in siblings:
                if element_contains_text:
                    previous_sibling_selector: str | None = (
                        SoupDomUtils.generate_unique_css_selector(
                            sibling,
                            soup,
                            check_siblings=False,
                            check_parents=False,
                            check_children=False,
                            only_return_unique_selectors=False,
                            text_exclusions=list(element.stripped_strings),
                        )
                    )
                else:
                    previous_sibling_selector = (
                        SoupDomUtils.generate_unique_css_selector(
                            sibling,
                            soup,
                            check_siblings=False,
                            check_parents=False,
                            check_children=False,
                            only_return_unique_selectors=False,
                        )
                    )
                if previous_sibling_selector:
                    if SoupDomUtils.is_selector_unique(
                        soup, f"{previous_sibling_selector} + {''.join(steps)}"
                    ):
                        return f"{previous_sibling_selector} + {''.join(steps)}"
                    if SoupDomUtils.is_selector_unique(
                        soup,
                        f"{previous_sibling_selector} + {''.join(steps)}{''.join(text_steps)}",
                    ):
                        return f"{previous_sibling_selector} + {''.join(steps)}{''.join(text_steps)}"

            siblings = element.find_next_siblings()
            for sibling in siblings:
                next_sibling_selector: str | None = SoupDomUtils.generate_unique_css_selector(
                    sibling,
                    soup,
                    check_siblings=False,
                    check_parents=False,
                    check_children=False,
                    only_return_unique_selectors=False,
                )
                if next_sibling_selector:
                    sibling_selector: str = (
                        f"{''.join(steps)}:has(+ {next_sibling_selector})"
                    )
                    if SoupDomUtils.is_selector_unique(soup, sibling_selector):
                        return sibling_selector

        if check_parents:
            parent_level: int = 0
            max_level: int = 10
            # Step 5: Parent and Sibling Relationships
            parent_selectors: List[str] = []
            for parent in element.parents:
                if (
                    parent
                    and not SoupDomUtils.has_child_dialog_without_open(parent)
                    and parent.name != "[document]"
                ):
                    parent_level += 1
                    if parent_level <= max_level:
                        if element_contains_text:
                            parent_selector: str | None = SoupDomUtils.generate_unique_css_selector(
                                parent,
                                soup,
                                check_children=False,
                                check_siblings=True,
                                check_parents=False,
                                check_text=True,
                                only_return_unique_selectors=False,
                                text_exclusions=list(element.stripped_strings),
                            )
                        else:
                            parent_selector = SoupDomUtils.generate_unique_css_selector(
                                parent,
                                soup,
                                check_children=False,
                                check_siblings=True,
                                check_parents=False,
                                check_text=True,
                                only_return_unique_selectors=False,
                            )
                        if parent_selector:
                            parent_selectors.append(parent_selector)
                            parent_child_selector: str = f"{' > '.join(reversed(parent_selectors))} > {''.join(steps)}"
                            current_parent_child_selector: str = (
                                f"{parent_selector} {''.join(steps)}"
                            )
                            if SoupDomUtils.is_selector_unique(
                                soup, current_parent_child_selector
                            ):
                                return current_parent_child_selector
                            elif SoupDomUtils.is_selector_unique(
                                soup, parent_child_selector
                            ):
                                return parent_child_selector

        if only_return_unique_selectors:
            if SoupDomUtils.is_selector_unique(soup, "".join(steps)):
                return "".join(steps)
            else:
                parent: Tag | None = element.find_parent()
                siblings: List[Tag] = parent.find_all(element.name) if parent else []
                if len(siblings) > 1:
                    index: int = siblings.index(element) + 1
                    return f"{''.join(steps)}:nth-of-type({index})"
        else:
            return "".join(steps)

    @staticmethod
    def has_display_none(tag: Tag) -> bool:
        """Checks if the tag has a style attribute with 'display: none'.

        Args:
            tag (Tag): The BeautifulSoup Tag to check.

        Returns:
            bool: True if the tag has 'display: none' in its style attribute, False otherwise.
        """
        style: str = tag.get("style", "")
        return "display: none" in style

    @staticmethod
    @log
    def get_simplified_dom_tree(source: str) -> str | None:
        """Returns a simplified DOM tree as a string, removing non-essential elements and attributes.

        Parses the HTML source, removes scripts, SVGs, templates, navigation, hidden elements,
        and unnecessary attributes to produce a cleaner DOM representation for analysis.

        Args:
            source (str): The HTML source code as a string.

        Returns:
            str | None: The simplified DOM tree as a string, or None if no <body> is present.
        """
        soup: BeautifulSoup = BeautifulSoup(source, "html.parser")

        for elem in soup.find_all("script"):
            elem.decompose()

        for elem in soup.find_all("svg"):
            elem.decompose()

        for elem in soup.find_all("source"):
            elem.decompose()

        for elem in soup.find_all("animatetransform"):
            elem.decompose()

        # for elem in soup.find_all('footer'):
        #     elem.decompose()

        for elem in soup.find_all("template"):
            elem.decompose()

        for elem in soup.find_all("head"):
            elem.decompose()

        for elem in soup.find_all("nav"):
            elem.decompose()

        # Find all elements with 'display: none'
        hidden_elements: ResultSet = soup.find_all(SoupDomUtils().has_display_none)
        for element in hidden_elements:
            element.decompose()

        # Find all elements with 'display: none'
        hidden_elements = soup.find_all(attrs={"type": "hidden"})
        for element in hidden_elements:
            element.decompose()

        for a_tag in soup.find_all("a"):
            del a_tag["href"]
            del a_tag["class"]

        for tag in soup.find_all(style=True):
            del tag["style"]

        for section_tag in soup.find_all("section"):
            del section_tag["class"]

        for picture_tag in soup.find_all("picture"):
            del picture_tag["class"]

        for img_tag in soup.find_all("img"):
            del img_tag["class"]
            del img_tag["alt"]
            del img_tag["src"]

        attributes_to_keep: List[str] = [
            "id",
            "class",
            "value",
            "name",
            "type",
            "placeholder",
            "role",
        ]
        for tag in soup.find_all(True):  # True finds all tags
            for attr in list(tag.attrs):  # list() to avoid runtime error
                if attr not in attributes_to_keep:
                    del tag[attr]

        return str(soup.body)

    @staticmethod
    @log
    def generate_unique_xpath_selector(
            element: Tag | None,
            soup: BeautifulSoup,
            *,
            check_parents: bool = True,
            check_siblings: bool = True,
            check_children: bool = True,
            check_text: bool = True,
            only_return_unique_selectors: bool = True,
    ) -> str | None:
        """Generates a unique XPath selector for the given element within the soup.

        Attempts to build an XPath using tag name, attributes, text content, and relationships
        to parents and siblings. Returns the XPath if it uniquely identifies the element in the DOM.

        Args:
            element (Tag | None): The BeautifulSoup Tag for which to generate the XPath.
            soup (BeautifulSoup): The BeautifulSoup object representing the DOM.
            check_parents (bool): Whether to include parent relationships in the XPath.
            check_siblings (bool): Whether to include sibling relationships in the XPath.
            check_children (bool): Whether to include child relationships in the XPath.
            check_text (bool): Whether to include text content in the XPath.
            only_return_unique_selectors (bool): If True, only return selectors that are unique.

        Returns:
            str | None: A unique XPath selector string if found, otherwise None.
        """
        if element is None:
            return ""

        # Step 1: Tag
        steps: List[str] = []
        tag_xpath: str = f"{element.name}"
        steps.append(tag_xpath)

        if element.get("content-desc"):
            content_desc_xpath: str = f"[@content-desc='{element['content-desc']}']"
            content_desc_xpath_with_prefix: str = f"//{element.name}{content_desc_xpath}"
            if SoupDomUtils.is_xpath_unique(soup, content_desc_xpath_with_prefix):
                return content_desc_xpath_with_prefix
            if SoupDomUtils.is_xpath_multiple(soup, content_desc_xpath_with_prefix):
                steps.append(content_desc_xpath)

        if element.get("resource-id"):
            content_desc_xpath = f"[@resource-id='{element['resource-id']}']"
            content_desc_xpath_with_prefix = f"//{element.name}{content_desc_xpath}"
            if SoupDomUtils.is_xpath_unique(soup, content_desc_xpath_with_prefix):
                return content_desc_xpath_with_prefix
            if SoupDomUtils.is_xpath_multiple(soup, content_desc_xpath_with_prefix):
                steps.append(content_desc_xpath)

        if check_text:
            # Step 4: Text Content
            if element.text.strip():
                for text in element.stripped_strings:
                    sanitized_text: str = SoupDomUtils.clean_text_for_xpath(text)
                    if '"' in sanitized_text:
                        text_xpath: str = f"[contains(text(), '{sanitized_text}')]"
                    elif "'" in sanitized_text:
                        text_xpath = f'[contains(text(), "{sanitized_text}")]'
                    else:
                        text_xpath = f"[contains(text(), '{sanitized_text}')]"
                    if SoupDomUtils.is_xpath_unique(soup, f"//{element.name}{text_xpath}"):
                        return f"//{element.name}{text_xpath}"

            elif element.get("text"):
                sanitized_text = SoupDomUtils.clean_text_for_xpath(element["text"])
                if '"' in sanitized_text:
                    text_xpath = f"[contains(@text, '{sanitized_text}')]"
                elif "'" in sanitized_text:
                    text_xpath = f'[contains(@text, "{sanitized_text}")]'
                else:
                    text_xpath = f"[contains(@text, '{sanitized_text}')]"
                if SoupDomUtils.is_xpath_unique(soup, f"//{element.name}{text_xpath}"):
                    return f"//{element.name}{text_xpath}"
        # Step 2: ID
        if element.get("id"):
            id_xpath: str = f"[@id='{element['id']}']"
            id_xpath_with_prefix: str = f"//{element.name}{id_xpath}"
            if SoupDomUtils.is_xpath_unique(soup, id_xpath_with_prefix):
                return id_xpath_with_prefix
            if SoupDomUtils.is_xpath_multiple(soup, id_xpath_with_prefix):
                steps.append(id_xpath)

        if element.get("name"):
            name_xpath: str = f"[@name='{element['name']}']"
            name_xpath_with_prefix: str = f"//{element.name}{name_xpath}"
            if SoupDomUtils.is_xpath_unique(soup, name_xpath_with_prefix):
                return name_xpath_with_prefix
            if SoupDomUtils.is_xpath_multiple(soup, name_xpath_with_prefix):
                steps.append(name_xpath)

        if element.get("type"):
            type_xpath: str = f"[@type='{element['type']}']"
            type_xpath_with_prefix: str = f"//{element.name}{type_xpath}"
            if SoupDomUtils.is_xpath_unique(soup, type_xpath_with_prefix):
                return type_xpath_with_prefix
            if SoupDomUtils.is_xpath_multiple(soup, type_xpath_with_prefix):
                steps.append(type_xpath)

        if element.get("placeholder"):
            placeholder_xpath: str = f"[@placeholder='{element['placeholder']}']"
            placeholder_xpath_with_prefix: str = f"//{element.name}{placeholder_xpath}"
            if SoupDomUtils.is_xpath_unique(soup, placeholder_xpath_with_prefix):
                return placeholder_xpath_with_prefix
            if SoupDomUtils.is_xpath_multiple(soup, placeholder_xpath_with_prefix):
                steps.append(placeholder_xpath)

        if element.get("role"):
            role_xpath: str = f"[@role='{element['role']}']"
            role_xpath_with_prefix: str = f"//{element.name}{role_xpath}"
            if SoupDomUtils.is_xpath_unique(soup, role_xpath_with_prefix):
                return role_xpath_with_prefix
            if SoupDomUtils.is_xpath_multiple(soup, role_xpath_with_prefix):
                steps.append(role_xpath)

        # Step 3: Class
        if element.get("class"):
            # Build an XPath condition for all classes using "and"
            if isinstance(element["class"], list):
                filtered_classes: List[str] = [x for x in element["class"] if "hidden" not in x]
                class_conditions: str = " and ".join(
                    [f"contains(@class, '{cls}')" for cls in filtered_classes]
                )
                class_xpath: str = f"[{class_conditions}]"
            if isinstance(element["class"], str):
                class_xpath = f"[@class='{element['class']}']"
            class_xpath_with_prefix: str = f"//{element.name}{class_xpath}"
            if SoupDomUtils.is_xpath_unique(soup, class_xpath_with_prefix):
                return class_xpath_with_prefix
            if SoupDomUtils.is_xpath_multiple(soup, class_xpath_with_prefix):
                steps.append(class_xpath)

        if check_text:
            # Step 4: Text Content

            if element.text.strip():
                for text in element.stripped_strings:
                    element_contains_text: bool = True
                    sanitized_text = SoupDomUtils.clean_text_for_xpath(text)
                    if '"' in sanitized_text:
                        text_xpath = f"[contains(text(), '{sanitized_text}')]"
                    elif "'" in sanitized_text:
                        text_xpath = f'[contains(text(), "{sanitized_text}")]'
                    else:
                        text_xpath = f"[contains(text(), '{sanitized_text}')]"
                    if SoupDomUtils.is_xpath_unique(soup, f"//{element.name}{text_xpath}"):
                        return f"//{element.name}{text_xpath}"
                    elif SoupDomUtils.is_xpath_unique(soup, f"//*{text_xpath}"):
                        return f"//*{text_xpath}"
                    elif SoupDomUtils.is_xpath_multiple(soup, f"//{element.name}{text_xpath}"):
                        steps.append(text_xpath)
                    elif SoupDomUtils.is_xpath_multiple(soup, f"//*{text_xpath}"):
                        steps.append(f"//*{text_xpath}")

            elif element.get("text"):
                element_contains_text = True
                sanitized_text = SoupDomUtils.clean_text_for_xpath(element["text"])
                if '"' in sanitized_text:
                    text_xpath = f"[contains(@text, '{sanitized_text}')]"
                elif "'" in sanitized_text:
                    text_xpath = f'[contains(@text, "{sanitized_text}")]'
                else:
                    text_xpath = f"[contains(@text, '{sanitized_text}')]"
                if SoupDomUtils.is_xpath_unique(soup, f"//{element.name}{text_xpath}"):
                    return f"//{element.name}{text_xpath}"
                elif SoupDomUtils.is_xpath_multiple(soup, f"//{element.name}{text_xpath}"):
                    steps.append(text_xpath)

        if SoupDomUtils.is_xpath_unique(soup, f"//{''.join(steps)}"):
            return f"//{''.join(steps)}"

        if check_parents:
            # Step 5: Parent Relationships
            parent: Tag | None = element.parent
            if parent:
                parent_xpath: str | None = SoupDomUtils.generate_unique_xpath_selector(parent, soup)
                if parent_xpath:
                    index: int = parent.find_all(element.name).index(element) + 1
                    parent_child_xpath: str = f"{parent_xpath}/{element.name}[{index}]"
                    if SoupDomUtils.is_xpath_unique(soup, parent_child_xpath):
                        return parent_child_xpath

        if check_siblings:
            # Step 6: Sibling Relationships
            siblings = element.find_previous_siblings(element.name)
            for sibling in siblings:
                previous_sibling_selector = SoupDomUtils.generate_unique_xpath_selector(
                    sibling,
                    soup,
                    check_siblings=False,
                    check_parents=False,
                    check_children=False,
                )
                if previous_sibling_selector:
                    sibling_selector: str = (
                        f"{previous_sibling_selector}/following-sibling::{''.join(steps)}"
                    )
                    if SoupDomUtils.is_xpath_unique(soup, sibling_selector):
                        return sibling_selector

            siblings = element.find_next_siblings()
            for sibling in siblings:
                next_sibling_selector = SoupDomUtils.generate_unique_xpath_selector(
                    sibling,
                    soup,
                    check_siblings=False,
                    check_parents=False,
                    check_children=False,
                )
                if next_sibling_selector:
                    sibling_selector = (
                        f"{next_sibling_selector}/preceding-sibling::{''.join(steps)}"
                    )
                    if SoupDomUtils.is_xpath_unique(soup, sibling_selector):
                        return sibling_selector

        if check_parents:
            parent_level: int = 0
            max_level: int = 10
            # Step 5: Parent and Sibling Relationships
            parent_selectors: List[str] = []
            for parent in element.parents:
                if (
                        parent
                        and not SoupDomUtils.has_child_dialog_without_open(parent)
                        and parent.name != "[document]"
                ):
                    parent_level += 1
                    if parent_level <= max_level:
                        parent_selector = SoupDomUtils.generate_unique_xpath_selector(
                            parent,
                            soup,
                            check_children=False,
                            check_siblings=True,
                            check_parents=False,
                            check_text=True,
                            only_return_unique_selectors=False,
                        )
                        if parent_selector:
                            parent_selectors.append(parent_selector)
                            parent_child_selector = (
                                f"{'/'.join(reversed(parent_selectors))}/{''.join(steps)}"
                            )
                            current_parent_child_selector = (
                                f"{parent_selector}//{''.join(steps)}"
                            )
                            if SoupDomUtils.is_selector_unique(soup, current_parent_child_selector):
                                return current_parent_child_selector
                            elif SoupDomUtils.is_selector_unique(soup, parent_child_selector):
                                return parent_child_selector

        # if check_children:
        #     # Step 7: Child Relationships
        #     children = element.find_all(recursive=False)
        #     for child in children:
        #         child_text = clean_text_for_xpath(child.text)
        #         if child_text:
        #             if '"' in child_text:
        #                 child_text_xpath = f"{element.name}/{child.name}[contains(text(), '{child_text}')]"
        #             elif "'" in child_text:
        #                 child_text_xpath = f'{element.name}/{child.name}[contains(text(), "{child_text}")]'
        #             else:
        #                 child_text_xpath = f"{element.name}/{child.name}[contains(text(), '{child_text}')]"

        #             if is_xpath_unique(soup, child_text_xpath):
        #                 return child_text_xpath

        if only_return_unique_selectors:
            if SoupDomUtils.is_xpath_unique(soup, f"//{''.join(steps)}"):
                # Combine steps into a final XPath
                return f"//{''.join(steps)}"
        else:
            if SoupDomUtils.is_xpath_unique(soup, f"//{''.join(steps)}") or SoupDomUtils.is_xpath_multiple(
                    soup, f"//{''.join(steps)}"
            ):
                return f"//{''.join(steps)}"

    @staticmethod
    def is_xpath_unique(soup: BeautifulSoup, xpath: str) -> bool:
        """Checks if the XPath selector matches exactly one element in the DOM.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object representing the DOM.
            xpath (str): The XPath selector to check.

        Returns:
            bool: True if exactly one element matches the XPath, False otherwise.
        """
        try:
            if soup.is_xml:
                tree = etree.XML(str(soup.hierarchy), parser=etree.HTMLParser())
            else:
                tree = etree.HTML(str(soup), parser=etree.HTMLParser())
        except Exception as e:
            print(f"Error in is_xpath_unique: {e}\nXpath: {xpath}")
            return False
        try:
            # Use the XPath to find matching elements
            elements: List[etree._Element] = tree.xpath(xpath)
            # Return True if exactly one element matches
            return len(elements) == 1
        except Exception as e:
            print(f"Error in is_xpath_unique: {e}\nXpath: {xpath}")
            return False

    @staticmethod
    def is_xpath_multiple(soup: BeautifulSoup, xpath: str) -> bool:
        """Checks if the XPath selector matches multiple elements in the DOM.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object representing the DOM.
            xpath (str): The XPath selector to check.

        Returns:
            bool: True if more than one element matches the XPath, False otherwise.
        """
        try:
            # Parse the HTML content using lxml
            tree = etree.HTML(str(soup), parser=etree.HTMLParser())
        except:
            try:
                tree = etree.HTML(str(soup.hierarchy), parser=etree.HTMLParser())
            except Exception as e:
                print(f"Error in is_xpath_unique: {e}\nXpath: {xpath}")
                return False
        try:
            # Use the XPath to find matching elements
            elements: List[etree._Element] = tree.xpath(xpath)
            # Return True if more than one element matches
            return len(elements) > 1
        except Exception as e:
            print(f"Error in is_xpath_multiple: {e}")
            return False

    @staticmethod
    def clean_text_for_xpath(text: str) -> str:
        """Sanitizes text for use in an XPath expression.

        Removes leading/trailing whitespace and collapses internal whitespace to a single space.

        Args:
            text (str): The text to sanitize.

        Returns:
            str: The sanitized text suitable for use in an XPath expression.
        """
        return re.sub(r"\s+", " ", text.strip())
