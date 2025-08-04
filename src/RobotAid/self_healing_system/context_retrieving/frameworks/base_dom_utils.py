import re
from abc import ABC, abstractmethod
from typing import Optional

from lxml import etree


class BaseDomUtils(ABC):
    """Abstract base class for library-specific DOM utilities.

    This class defines the common interface that all DOM utility implementations
    must follow, ensuring consistency across different Robot Framework libraries.
    """

    def __init__(self, library_instance: Optional[object] = None):
        """Initialize the DOM utility with a library instance.

        Args:
            library_instance: An instance of the Robot Framework library.
        """
        self.library_instance = library_instance

    @abstractmethod
    def is_locator_valid(self, locator: str) -> bool:
        """Check if the given locator is valid in the DOM.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is valid, False otherwise.
        """
        pass

    @abstractmethod
    def is_locator_unique(self, locator: str) -> bool:
        """Check if the given locator is unique in the DOM.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is unique, False otherwise.
        """
        pass

    @abstractmethod
    def is_locator_visible(self, locator: str) -> bool:
        """Check if the given locator is visible in the DOM.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is visible, False otherwise.
        """
        pass

    @abstractmethod
    def get_dom_tree(self) -> str:
        """Retrieve the DOM tree of the current page.

        Returns:
            The DOM tree as a string.
        """
        pass

    @abstractmethod
    def get_library_type(self) -> str:
        """Get the library type identifier.

        Returns:
            The library type (e.g., 'browser', 'selenium', 'appium').
        """
        pass

    @abstractmethod
    def is_element_clickable(self, locator: str) -> bool:
        """Check if the element identified by the locator is clickable.

        Args:
            locator: The locator to check.

        Returns:
            True if the element is clickable, False otherwise.
        """
        pass

    @abstractmethod
    def get_locator_proposals(
        self, failed_locator: str, keyword_name: str
    ) -> list[str]:
        """Get proposals for the given locator.

        Args:
            locator: The locator to get proposals for.

        Returns:
            A list of proposed locators.
        """
        pass

    @abstractmethod
    def get_locator_metadata(self, locator: str) -> dict:
        """Get metadata for the given locator.

        Args:
            locator: The locator to get metadata for.

        Returns:
            A dictionary containing metadata about elements matching the locator.
            The dictionary may contain keys like 'tag', 'id', 'class', 'text', 'attributes', etc.
        """
        pass


def generate_unique_css_selector(
    element,
    soup,
    check_parents=True,
    check_siblings=True,
    check_children=True,
    check_text=True,
    only_return_unique_selectors=True,
    text_exclusions=[],
):
    steps = []
    text_steps = []

    element_contains_text = False

    tag_selector = f"{element.name}"
    steps.append(tag_selector)

    # If any parent is an frame or iframe, we need to add it

    # Step 2: ID
    if element.get("id"):
        id_selector = f"#{element['id']}"
        if is_selector_unique(soup, f"{element.name}{id_selector}"):
            return f"{element.name}{id_selector}"
        steps.append(id_selector)

    if element.get("name"):
        name_selector = f'[name="{element["name"]}"]'
        if is_selector_unique(soup, f"{element.name}{name_selector}"):
            return f"{element.name}{name_selector}"
        steps.append(name_selector)

    if element.get("type"):
        type_selector = f'[type="{element["type"]}"]'
        if is_selector_unique(soup, f"{element.name}{type_selector}"):
            return f"{element.name}{type_selector}"
        steps.append(type_selector)

    if element.get("placeholder"):
        placeholder_selector = f'[placeholder="{element["placeholder"]}"]'
        if is_selector_unique(soup, f"{element.name}{placeholder_selector}"):
            return f"{element.name}{placeholder_selector}"
        steps.append(placeholder_selector)

    if element.get("role"):
        role_selector = f'[role="{element["role"]}"]'
        if is_selector_unique(soup, f"{element.name}{role_selector}"):
            return f"{element.name}{role_selector}"
        steps.append(role_selector)

    # if check_text:
    #     # Step 4: Text Content
    #     if element.text.strip():
    #         for text in element.stripped_strings:
    #             sanitized_text = clean_text_for_selector(text)
    #             text_selector = f':-soup-contains("{sanitized_text}")'
    #             if is_selector_unique(soup, f"{element.name}{text_selector}"):
    #                 return f"{element.name}{text_selector}"
    #             elif is_selector_unique(soup, f"{element.name}{text_selector}"):
    #                 return f"{element.name}{text_selector}"

    # Step 3: Class
    if element.get("class"):
        filtered_classes = [x for x in element["class"] if "hidden" not in x]
        class_list = []
        class_selector = None
        for single_class in filtered_classes:
            class_list.append(single_class)
            class_selector = "." + ".".join(class_list)
            if is_selector_unique(soup, f"{element.name}{class_selector}"):
                return f"{element.name}{class_selector}"
        if class_selector:
            steps.append(class_selector)

    if check_text:
        text_selectors = []
        selector_count = 0
        # Step 4: Text Content
        if element.text.strip():
            element_contains_text = True
            if element.string and element.string not in text_exclusions:
                sanitized_text = clean_text_for_selector(element.string)
                text_selector = f':-soup-contains-own("{sanitized_text}")'
                selector_count = get_selector_count(
                    soup, f"{''.join(steps)}{text_selector}"
                )
                if selector_count == 1:
                    return f"{''.join(steps)}{text_selector}"
                elif selector_count > 1:
                    text_steps.append(text_selector)
            if not element.string or selector_count == 0:
                for text in element.stripped_strings:
                    if text not in text_exclusions:
                        sanitized_text = clean_text_for_selector(text)
                        text_selector = f':-soup-contains("{sanitized_text}")'
                        # if is_selector_unique(soup, f"{element.name}{text_selector}"):
                        #     return f"{element.name}{text_selector}"
                        text_selectors.append(text_selector)

                        selector_count = get_selector_count(
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
            ul_parent_selector = generate_unique_css_selector(
                element.find_parent("ul"),
                soup,
                check_parents=True,
                check_siblings=False,
                check_text=False,
                only_return_unique_selectors=False,
            )
            li_parent_selector = generate_unique_css_selector(
                element.find_parent("li"),
                soup,
                check_parents=False,
                check_siblings=False,
                check_text=False,
                only_return_unique_selectors=False,
            )
            ul_li_selector = (
                f"{ul_parent_selector} > {li_parent_selector} {''.join(steps)}"
            )
            if is_selector_unique(soup, ul_li_selector):
                return ul_li_selector
    elif element.find_parent("ul"):
        ul_parent_selector = generate_unique_css_selector(
            element.find_parent("ul"),
            soup,
            check_parents=True,
            check_siblings=False,
            check_text=False,
            only_return_unique_selectors=False,
        )
        ul_selector = f"{ul_parent_selector} > {''.join(steps)}"
        if is_selector_unique(soup, ul_selector):
            return ul_selector

    if check_siblings:
        # Step 7: Sibling Relationships
        siblings = element.find_previous_siblings()
        for sibling in siblings:
            if element_contains_text:
                previous_sibling_selector = generate_unique_css_selector(
                    sibling,
                    soup,
                    check_siblings=False,
                    check_parents=False,
                    check_children=False,
                    only_return_unique_selectors=False,
                    text_exclusions=list(element.stripped_strings),
                )
            else:
                previous_sibling_selector = generate_unique_css_selector(
                    sibling,
                    soup,
                    check_siblings=False,
                    check_parents=False,
                    check_children=False,
                    only_return_unique_selectors=False,
                )
            if previous_sibling_selector:
                if is_selector_unique(
                    soup, f"{previous_sibling_selector} + {''.join(steps)}"
                ):
                    return f"{previous_sibling_selector} + {''.join(steps)}"
                if is_selector_unique(
                    soup,
                    f"{previous_sibling_selector} + {''.join(steps)}{''.join(text_steps)}",
                ):
                    return f"{previous_sibling_selector} + {''.join(steps)}{''.join(text_steps)}"

        siblings = element.find_next_siblings()
        for sibling in siblings:
            next_sibling_selector = generate_unique_css_selector(
                sibling,
                soup,
                check_siblings=False,
                check_parents=False,
                check_children=False,
                only_return_unique_selectors=False,
            )
            if next_sibling_selector:
                sibling_selector = f"{''.join(steps)}:has(+ {next_sibling_selector})"
                if is_selector_unique(soup, sibling_selector):
                    return sibling_selector

    if check_parents:
        parent_level = 0
        max_level = 10
        # Step 5: Parent and Sibling Relationships
        parent_selectors = []
        for parent in element.parents:
            if (
                parent
                and not has_child_dialog_without_open(parent)
                and parent.name != "[document]"
            ):
                parent_level += 1
                if parent_level <= max_level:
                    if element_contains_text:
                        parent_selector = generate_unique_css_selector(
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
                        parent_selector = generate_unique_css_selector(
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
                        parent_child_selector = f"{' > '.join(reversed(parent_selectors))} > {''.join(steps)}"
                        current_parent_child_selector = (
                            f"{parent_selector} {''.join(steps)}"
                        )
                        if is_selector_unique(soup, current_parent_child_selector):
                            return current_parent_child_selector
                        elif is_selector_unique(soup, parent_child_selector):
                            return parent_child_selector

    if only_return_unique_selectors:
        if is_selector_unique(soup, "".join(steps)):
            return "".join(steps)
        else:
            parent = element.find_parent()
            siblings = parent.find_all(element.name)
            if len(siblings) > 1:
                index = siblings.index(element) + 1
                return f"{''.join(steps)}:nth-of-type({index})"
    else:
        return "".join(steps)


def get_selector_count(soup, selector):
    try:
        elements = soup.select(selector)
        return len(elements)
    except Exception:
        return 0


def is_selector_unique(soup, selector):
    """Check if the CSS selector matches only one element."""
    try:
        elements = soup.select(selector)
        return len(elements) == 1
    except Exception:
        return False


def is_selector_multiple(soup, selector):
    """Check if the CSS selector matches multiple elements."""
    try:
        elements = soup.select(selector)
        return len(elements) > 1
    except Exception:
        return False


def has_child_dialog_without_open(element):
    """Check if any parent of the given element is a <dialog> without the 'open' attribute."""
    try:
        dialog = [x for x in element.children if x.name == "dialog"]
        for d in dialog:
            if not d.has_attr("open"):
                return True
        return False
    except:
        return True


def clean_text_for_selector(text):
    """Sanitize text for use in a CSS selector."""
    return re.sub(r"\s+", " ", text.strip())


# Function to check if an element is a leaf or the lowest of its type in a branch
def is_leaf_or_lowest(element):
    # Check if the element has no child elements (leaf)
    if not element.find():
        return True

    # Check if the element is the lowest of its type in this branch
    tag_name = element.name
    if not element.find_all(tag_name):
        return True

    return False


def has_parent_dialog_without_open(element):
    """Check if any parent of the given element is a <dialog> without the 'open' attribute."""
    try:
        dialog = [x for x in element.parents if x.name == "dialog"]
        for d in dialog:
            if not d.has_attr("open"):
                return True
        return False
    except:
        return True


# Function to check if an element directly contains text
def has_direct_text(tag):
    # Check if the tag has any direct text (not in its children)
    return tag.string and tag.string.strip() and not tag.find()


def is_headline(tag):
    return tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]


def is_div_in_li(tag):
    # Check if the tag is a div
    if tag.name != "div":
        return False

    # Check if the parent of the tag is an li
    parent = tag.find_parent("li")
    return parent is not None


def is_p(tag):
    if tag.name == "p":
        return True
    else:
        return False


def generate_unique_xpath_selector(
    element,
    soup,
    check_parents=True,
    check_siblings=True,
    check_children=True,
    check_text=True,
    only_return_unique_selectors=True,
):
    """Generate a unique XPath for the given element."""
    if element is None:
        return ""

    # Step 1: Tag
    steps = []
    tag_xpath = f"{element.name}"
    steps.append(tag_xpath)

    if element.get("content-desc"):
        content_desc_xpath = f"[@content-desc='{element['content-desc']}']"
        content_desc_xpath_with_prefix = f"//{element.name}{content_desc_xpath}"
        if is_xpath_unique(soup, content_desc_xpath_with_prefix):
            return content_desc_xpath_with_prefix
        if is_xpath_multiple(soup, content_desc_xpath_with_prefix):
            steps.append(content_desc_xpath)

    if element.get("resource-id"):
        content_desc_xpath = f"[@resource-id='{element['resource-id']}']"
        content_desc_xpath_with_prefix = f"//{element.name}{content_desc_xpath}"
        if is_xpath_unique(soup, content_desc_xpath_with_prefix):
            return content_desc_xpath_with_prefix
        if is_xpath_multiple(soup, content_desc_xpath_with_prefix):
            steps.append(content_desc_xpath)

    if check_text:
        # Step 4: Text Content
        if element.text.strip():
            for text in element.stripped_strings:
                sanitized_text = clean_text_for_xpath(text)
                if '"' in sanitized_text:
                    text_xpath = f"[contains(text(), '{sanitized_text}')]"
                elif "'" in sanitized_text:
                    text_xpath = f'[contains(text(), "{sanitized_text}")]'
                else:
                    text_xpath = f"[contains(text(), '{sanitized_text}')]"
                if is_xpath_unique(soup, f"//{element.name}{text_xpath}"):
                    return f"//{element.name}{text_xpath}"

        elif element.get("text"):
            sanitized_text = clean_text_for_xpath(element["text"])
            if '"' in sanitized_text:
                text_xpath = f"[contains(@text, '{sanitized_text}')]"
            elif "'" in sanitized_text:
                text_xpath = f'[contains(@text, "{sanitized_text}")]'
            else:
                text_xpath = f"[contains(@text, '{sanitized_text}')]"
            if is_xpath_unique(soup, f"//{element.name}{text_xpath}"):
                return f"//{element.name}{text_xpath}"
    # Step 2: ID
    if element.get("id"):
        id_xpath = f"[@id='{element['id']}']"
        id_xpath_with_prefix = f"//{element.name}{id_xpath}"
        if is_xpath_unique(soup, id_xpath_with_prefix):
            return id_xpath_with_prefix
        if is_xpath_multiple(soup, id_xpath_with_prefix):
            steps.append(id_xpath)

    if element.get("name"):
        name_xpath = f"[@name='{element['name']}']"
        name_xpath_with_prefix = f"//{element.name}{name_xpath}"
        if is_xpath_unique(soup, name_xpath_with_prefix):
            return name_xpath_with_prefix
        if is_xpath_multiple(soup, name_xpath_with_prefix):
            steps.append(name_xpath)

    if element.get("type"):
        type_xpath = f"[@type='{element['type']}']"
        type_xpath_with_prefix = f"//{element.name}{type_xpath}"
        if is_xpath_unique(soup, type_xpath_with_prefix):
            return type_xpath_with_prefix
        if is_xpath_multiple(soup, type_xpath_with_prefix):
            steps.append(type_xpath)

    if element.get("placeholder"):
        placeholder_xpath = f"[@placeholder='{element['placeholder']}']"
        placeholder_xpath_with_prefix = f"//{element.name}{placeholder_xpath}"
        if is_xpath_unique(soup, placeholder_xpath_with_prefix):
            return placeholder_xpath_with_prefix
        if is_xpath_multiple(soup, placeholder_xpath_with_prefix):
            steps.append(placeholder_xpath)

    if element.get("role"):
        role_xpath = f"[@role='{element['role']}']"
        role_xpath_with_prefix = f"//{element.name}{role_xpath}"
        if is_xpath_unique(soup, role_xpath_with_prefix):
            return role_xpath_with_prefix
        if is_xpath_multiple(soup, role_xpath_with_prefix):
            steps.append(role_xpath)

    # Step 3: Class
    if element.get("class"):
        # Build an XPath condition for all classes using "and"
        if isinstance(element["class"], list):
            filtered_classes = [x for x in element["class"] if "hidden" not in x]
            class_conditions = " and ".join(
                [f"contains(@class, '{cls}')" for cls in filtered_classes]
            )
            class_xpath = f"[{class_conditions}]"
        if isinstance(element["class"], str):
            class_xpath = f"[@class='{element['class']}']"
        class_xpath_with_prefix = f"//{element.name}{class_xpath}"
        if is_xpath_unique(soup, class_xpath_with_prefix):
            return class_xpath_with_prefix
        if is_xpath_multiple(soup, class_xpath_with_prefix):
            steps.append(class_xpath)

    if check_text:
        # Step 4: Text Content

        if element.text.strip():
            for text in element.stripped_strings:
                element_contains_text = True
                sanitized_text = clean_text_for_xpath(text)
                if '"' in sanitized_text:
                    text_xpath = f"[contains(text(), '{sanitized_text}')]"
                elif "'" in sanitized_text:
                    text_xpath = f'[contains(text(), "{sanitized_text}")]'
                else:
                    text_xpath = f"[contains(text(), '{sanitized_text}')]"
                if is_xpath_unique(soup, f"//{element.name}{text_xpath}"):
                    return f"//{element.name}{text_xpath}"
                elif is_xpath_unique(soup, f"//*{text_xpath}"):
                    return f"//*{text_xpath}"
                elif is_xpath_multiple(soup, f"//{element.name}{text_xpath}"):
                    steps.append(text_xpath)
                elif is_xpath_multiple(soup, f"//*{text_xpath}"):
                    steps.append(f"//*{text_xpath}")

        elif element.get("text"):
            element_contains_text = True
            sanitized_text = clean_text_for_xpath(element["text"])
            if '"' in sanitized_text:
                text_xpath = f"[contains(@text, '{sanitized_text}')]"
            elif "'" in sanitized_text:
                text_xpath = f'[contains(@text, "{sanitized_text}")]'
            else:
                text_xpath = f"[contains(@text, '{sanitized_text}')]"
            if is_xpath_unique(soup, f"//{element.name}{text_xpath}"):
                return f"//{element.name}{text_xpath}"
            elif is_xpath_multiple(soup, f"//{element.name}{text_xpath}"):
                steps.append(text_xpath)

    if is_xpath_unique(soup, f"//{''.join(steps)}"):
        return f"//{''.join(steps)}"

    if check_parents:
        # Step 5: Parent Relationships
        parent = element.parent
        if parent:
            parent_xpath = generate_unique_xpath_selector(parent, soup)
            if parent_xpath:
                index = parent.find_all(element.name).index(element) + 1
                parent_child_xpath = f"{parent_xpath}/{element.name}[{index}]"
                if is_xpath_unique(soup, parent_child_xpath):
                    return parent_child_xpath

    if check_siblings:
        # Step 6: Sibling Relationships
        siblings = element.find_previous_siblings(element.name)
        for sibling in siblings:
            previous_sibling_selector = generate_unique_xpath_selector(
                sibling,
                soup,
                check_siblings=False,
                check_parents=False,
                check_children=False,
            )
            if previous_sibling_selector:
                sibling_selector = (
                    f"{previous_sibling_selector}/following-sibling::{''.join(steps)}"
                )
                if is_xpath_unique(soup, sibling_selector):
                    return sibling_selector

        siblings = element.find_next_siblings()
        for sibling in siblings:
            next_sibling_selector = generate_unique_xpath_selector(
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
                if is_xpath_unique(soup, sibling_selector):
                    return sibling_selector

    if check_parents:
        parent_level = 0
        max_level = 10
        # Step 5: Parent and Sibling Relationships
        parent_selectors = []
        for parent in element.parents:
            if (
                parent
                and not has_child_dialog_without_open(parent)
                and parent.name != "[document]"
            ):
                parent_level += 1
                if parent_level <= max_level:
                    parent_selector = generate_unique_xpath_selector(
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
                        if is_selector_unique(soup, current_parent_child_selector):
                            return current_parent_child_selector
                        elif is_selector_unique(soup, parent_child_selector):
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
        if is_xpath_unique(soup, f"//{''.join(steps)}"):
            # Combine steps into a final XPath
            return f"//{''.join(steps)}"
    else:
        if is_xpath_unique(soup, f"//{''.join(steps)}") or is_xpath_multiple(
            soup, f"//{''.join(steps)}"
        ):
            return f"//{''.join(steps)}"


def is_xpath_unique(soup, xpath):
    """Check if the XPath selector matches only one element."""
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
        elements = tree.xpath(xpath)
        # Return True if exactly one element matches
        return len(elements) == 1
    except Exception as e:
        print(f"Error in is_xpath_unique: {e}\nXpath: {xpath}")
        return False


def is_xpath_multiple(soup, xpath):
    """Check if the XPath selector matches multiple elements."""
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
        elements = tree.xpath(xpath)
        # Return True if more than one element matches
        return len(elements) > 1
    except Exception as e:
        print(f"Error in is_xpath_multiple: {e}")
        return False


def clean_text_for_xpath(text):
    """Sanitize text for use in an XPath expression."""
    return re.sub(r"\s+", " ", text.strip())
