import re
from bs4 import BeautifulSoup, Tag, NavigableString
from typing import Any, List, Optional, Union

class SoupDomUtils:
    """
    A utility class to operate on the DOM of a web page using BeautifulSoup.
    It provides methods to check, extract and manipulate HTML elements.
    """
    @staticmethod
    def clean_text_for_selector(text: str) -> str:
        """Sanitize text for use in a CSS selector."""
        return re.sub(r'\s+', ' ', text.strip())

    @staticmethod
    def get_selector_count(soup: BeautifulSoup, selector: str) -> int:
        try:
            elements = soup.select(selector)
            return len(elements)
        except Exception:
            return 0
    
    @staticmethod
    def is_selector_unique(soup: BeautifulSoup, selector: str) -> bool:
        """Check if the CSS selector matches only one element."""
        try:
            elements = soup.select(selector)
            return len(elements) == 1
        except Exception:
            return False
    
    @staticmethod
    def is_selector_multiple(soup: BeautifulSoup, selector: str) -> bool:
        """Check if the CSS selector matches multiple elements."""
        try:
            elements = soup.select(selector)
            return len(elements) > 1
        except Exception:
            return False

    @staticmethod
    def has_child_dialog_without_open(element: Tag) -> bool:
        """Check if any parent of the given element is a <dialog> without the 'open' attribute."""
        try:
            dialog = [x for x in element.children if isinstance(x, Tag) and x.name == "dialog"]
            for d in dialog:
                if not d.has_attr('open'):
                        return True
            return False
        except Exception:
            return True

    @staticmethod    
    def is_headline(tag: Tag) -> bool:
        return tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

    @staticmethod
    def is_div_in_li(tag: Tag) -> bool:
        # Check if the tag is a div
        if tag.name != 'div':
            return False
        
        # Check if the parent of the tag is an li
        parent = tag.find_parent('li')
        return parent is not None

    @staticmethod
    def is_p(tag: Tag) -> bool:
        if tag.name == 'p':
            return True
        else:
            return False

    @staticmethod
    def has_parent_dialog_without_open(element: Tag) -> bool:
        """Check if any parent of the given element is a <dialog> without the 'open' attribute."""
        try:
            dialog = [x for x in element.parents if isinstance(x, Tag) and x.name == "dialog"]
            for d in dialog:
                if not d.has_attr('open'):
                        return True
            return False
        except Exception:
            return True

    @staticmethod
    def is_leaf_or_lowest(element: Tag) -> bool:
        # Check if the element has no child elements (leaf)
        if not element.find():
            return True

        # Check if the element is the lowest of its type in this branch
        tag_name = element.name
        if not element.find_all(tag_name):
            return True

        return False

    @staticmethod
    def has_direct_text(tag: Tag) -> bool:
        # Check if the tag has any direct text (not in its children)
        return tag.string is not None and tag.string.strip() and not tag.find()

    @staticmethod
    def generate_unique_css_selector(
        element: Tag,
        soup: BeautifulSoup,
        check_parents: bool = True,
        check_siblings: bool = True,
        check_children: bool = True,
        check_text: bool = True,
        only_return_unique_selectors: bool = True,
        text_exclusions: Optional[List[str]] = None
    ) -> Optional[str]:
        steps: List[str] = []
        text_steps: List[str] = []
        
        element_contains_text: bool = False
        if text_exclusions is None:
            text_exclusions = []

        tag_selector: str = f"{element.name}"
        steps.append(tag_selector)
    
        # Step 2: ID
        if element.get('id'):
            id_selector = f"#{element['id']}"
            if SoupDomUtils.is_selector_unique(soup, f"{element.name}{id_selector}"):
                return f"{element.name}{id_selector}"
            steps.append(id_selector)
                
        if element.get('name'):
            name_selector = f'[name="{element["name"]}"]'
            if SoupDomUtils.is_selector_unique(soup, f"{element.name}{name_selector}"):
                return f"{element.name}{name_selector}"
            steps.append(name_selector)

        if element.get('type'):
            type_selector = f'[type="{element["type"]}"]'
            if SoupDomUtils.is_selector_unique(soup, f"{element.name}{type_selector}"):
                return f"{element.name}{type_selector}"
            steps.append(type_selector)

        if element.get('placeholder'):
            placeholder_selector = f'[placeholder="{element["placeholder"]}"]'
            if SoupDomUtils.is_selector_unique(soup, f"{element.name}{placeholder_selector}"):
                return f"{element.name}{placeholder_selector}"
            steps.append(placeholder_selector)

        if element.get('role'):
            role_selector = f'[role="{element["role"]}"]'
            if SoupDomUtils.is_selector_unique(soup, f"{element.name}{role_selector}"):
                return f"{element.name}{role_selector}"
            steps.append(role_selector)

        if element.get('class'):
            filtered_classes = [x for x in element['class'] if "hidden" not in x]
            class_list: List[str] = []
            class_selector: Optional[str] = None
            for single_class in filtered_classes:
                class_list.append(single_class)
                class_selector = "." + ".".join(class_list)
                if SoupDomUtils.is_selector_unique(soup, f"{element.name}{class_selector}"):
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
                    sanitized_text = SoupDomUtils.clean_text_for_selector(element.string)
                    text_selector = f':-soup-contains-own("{sanitized_text}")'
                    selector_count = SoupDomUtils.get_selector_count(soup, f"{''.join(steps)}{text_selector}")
                    if selector_count == 1:
                        return f"{''.join(steps)}{text_selector}"
                    elif selector_count >1:
                        text_steps.append(text_selector)
                if not element.string or selector_count==0:
                    for text in element.stripped_strings:
                        if text not in text_exclusions:
                            sanitized_text = SoupDomUtils.clean_text_for_selector(text)
                            text_selector = f':-soup-contains("{sanitized_text}")'
                            text_selectors.append(text_selector)

                            selector_count = SoupDomUtils.get_selector_count(soup, f"{''.join(steps)}{''.join(text_selectors)}")
                            if selector_count == 1:
                                return f"{''.join(steps)}{''.join(text_selectors)}"
                            elif selector_count >1:
                                text_steps.append(text_selector)
                            elif selector_count == 0:
                                break

        # Special check for items inside li/ul
        if element.find_parent("li"):
            if element.find_parent("ul"):
                ul_parent_selector = SoupDomUtils.generate_unique_css_selector(element.find_parent("ul"), soup, check_parents=True, check_siblings=False, check_text=False, only_return_unique_selectors=False)
                li_parent_selector = SoupDomUtils.generate_unique_css_selector(element.find_parent("li"), soup, check_parents=False, check_siblings=False, check_text=False, only_return_unique_selectors=False)
                ul_li_selector = f"{ul_parent_selector} > {li_parent_selector} {''.join(steps)}"
                if SoupDomUtils.is_selector_unique(soup, ul_li_selector):
                    return ul_li_selector 
        elif element.find_parent("ul"):
                ul_parent_selector = SoupDomUtils.generate_unique_css_selector(element.find_parent("ul"), soup, check_parents=True, check_siblings=False, check_text=False, only_return_unique_selectors=False)
                ul_selector = f"{ul_parent_selector} > {''.join(steps)}"
                if SoupDomUtils.is_selector_unique(soup, ul_selector):
                    return ul_selector 

        if check_siblings:
            # Step 7: Sibling Relationships
            siblings = element.find_previous_siblings()
            for sibling in siblings:
                if element_contains_text:
                    previous_sibling_selector = SoupDomUtils.generate_unique_css_selector(sibling, soup, check_siblings=False, check_parents=False, check_children=False, only_return_unique_selectors=False, text_exclusions=list(element.stripped_strings))
                else:
                    previous_sibling_selector = SoupDomUtils.generate_unique_css_selector(sibling, soup, check_siblings=False, check_parents=False, check_children=False, only_return_unique_selectors=False)
                if previous_sibling_selector:
                    if SoupDomUtils.is_selector_unique(soup, f"{previous_sibling_selector} + {''.join(steps)}"):
                        return f"{previous_sibling_selector} + {''.join(steps)}"
                    if SoupDomUtils.is_selector_unique(soup, f"{previous_sibling_selector} + {''.join(steps)}{''.join(text_steps)}"):
                        return f"{previous_sibling_selector} + {''.join(steps)}{''.join(text_steps)}"
                    

            siblings = element.find_next_siblings()
            for sibling in siblings:
                next_sibling_selector = SoupDomUtils.generate_unique_css_selector(sibling, soup, check_siblings=False, check_parents=False, check_children=False, only_return_unique_selectors=False)
                if next_sibling_selector:
                    sibling_selector = f"{''.join(steps)}:has(+ {next_sibling_selector})"
                    if SoupDomUtils.is_selector_unique(soup, sibling_selector):
                        return sibling_selector
        
        if check_parents:
            parent_level: int = 0
            max_level: int = 10
            # Step 5: Parent and Sibling Relationships
            parent_selectors: List[str] = []
            for parent in element.parents:
                if parent and not SoupDomUtils.has_child_dialog_without_open(parent) and parent.name != "[document]":
                    parent_level += 1
                    if parent_level <= max_level:
                        if element_contains_text:
                            parent_selector = SoupDomUtils.generate_unique_css_selector(parent, soup, check_children=False, check_siblings=True, check_parents=False, check_text=True, only_return_unique_selectors=False, text_exclusions=list(element.stripped_strings))
                        else:
                            parent_selector = SoupDomUtils.generate_unique_css_selector(parent, soup, check_children=False, check_siblings=True, check_parents=False, check_text=True, only_return_unique_selectors=False)
                        if parent_selector:
                            parent_selectors.append(parent_selector)
                            parent_child_selector = f"{' > '.join(reversed(parent_selectors))} > {''.join(steps)}"
                            current_parent_child_selector = f"{parent_selector} {''.join(steps)}"
                            if SoupDomUtils.is_selector_unique(soup, current_parent_child_selector):
                                return current_parent_child_selector                        
                            elif SoupDomUtils.is_selector_unique(soup, parent_child_selector):
                                return parent_child_selector

        if only_return_unique_selectors:
            if SoupDomUtils.is_selector_unique(soup, ''.join(steps)):
                return ''.join(steps)
            else:
                parent = element.find_parent()
                siblings = parent.find_all(element.name) if parent else []
                if len(siblings) > 1:
                    index = siblings.index(element) + 1
                    return f"{''.join(steps)}:nth-of-type({index})"
        else:
            return ''.join(steps)

    @staticmethod
    def has_display_none(tag):
        style = tag.get('style', '')
        return 'display: none' in style

    @staticmethod
    def get_simplified_dom_tree(source):
        soup = BeautifulSoup(source, 'html.parser')

        # Remove all <script> tags
        for elem in soup.find_all('script'):
            elem.decompose()


        # Remove all <svg> tags
        for elem in soup.find_all('svg'):
            elem.decompose()

        for elem in soup.find_all('source'):
            elem.decompose()

        for elem in soup.find_all('animatetransform'):
            elem.decompose()

        # for elem in soup.find_all('footer'):
        #     elem.decompose()

        for elem in soup.find_all('template'):
            elem.decompose()

        for elem in soup.find_all('head'):
            elem.decompose()

        for elem in soup.find_all('nav'):
            elem.decompose()

        # Find all elements with 'display: none'
        hidden_elements = soup.find_all(SoupDomUtils().has_display_none)
        # Remove these elements
        for element in hidden_elements:
            element.decompose()

        # Find all elements with 'display: none'
        hidden_elements = soup.find_all(attrs={"type": "hidden"})
        # Remove these elements
        for element in hidden_elements:
            element.decompose()

        for a_tag in soup.find_all('a'):
            del a_tag['href']
            del a_tag['class']
            
        for tag in soup.find_all(style=True):
            del tag['style']

        for section_tag in soup.find_all('section'):
            del section_tag['class']

        for picture_tag in soup.find_all('picture'):
            del picture_tag['class']

        for img_tag in soup.find_all('img'):
            del img_tag['class']
            del img_tag['alt']
            del img_tag['src']

        attributes_to_keep = ['id', 'class', 'value', 'name', 'type', 'placeholder', 'role']
        for tag in soup.find_all(True):  # True finds all tags
            for attr in list(tag.attrs):  # list() to avoid runtime error
                if attr not in attributes_to_keep:
                    del tag[attr]

        return str(soup.body)