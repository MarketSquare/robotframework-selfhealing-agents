import re
from bs4 import BeautifulSoup

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
    def get_selector_count(soup, selector):
        try:
            elements = soup.select(selector)
            return len(elements)
        except Exception:
            return 0
    
    @staticmethod
    def is_selector_unique(soup, selector):
        """Check if the CSS selector matches only one element."""
        try:
            elements = soup.select(selector)
            return len(elements) == 1
        except Exception:
            return False
    
    @staticmethod
    def is_selector_multiple(soup, selector):
        """Check if the CSS selector matches multiple elements."""
        try:
            elements = soup.select(selector)
            return len(elements) > 1
        except Exception:
            return False

    @staticmethod
    def has_child_dialog_without_open(element):
        """Check if any parent of the given element is a <dialog> without the 'open' attribute."""
        try:
            dialog = [x for x in element.children if x.name == "dialog"]
            for d in dialog:
                if not d.has_attr('open'):
                        return True
            return False
        except:
            return True


    @staticmethod    
    def is_headline(tag):
        return tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

    @staticmethod
    def is_div_in_li(tag):
        # Check if the tag is a div
        if tag.name != 'div':
            return False
        
        # Check if the parent of the tag is an li
        parent = tag.find_parent('li')
        return parent is not None

    @staticmethod
    def is_p(tag):
        if tag.name == 'p':
            return True
        else:
            return False

    @staticmethod
    def has_parent_dialog_without_open(element):
        """Check if any parent of the given element is a <dialog> without the 'open' attribute."""
        try:
            dialog = [x for x in element.parents if x.name == "dialog"]
            for d in dialog:
                if not d.has_attr('open'):
                        return True
            return False
        except:
            return True

    @staticmethod
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

    @staticmethod
     # Function to check if an element directly contains text
    def has_direct_text(tag):
        # Check if the tag has any direct text (not in its children)
        return tag.string and tag.string.strip() and not tag.find()

    @staticmethod
    def generate_unique_css_selector(element, soup, check_parents = True, check_siblings = True, check_children = True, check_text = True, only_return_unique_selectors=True, text_exclusions=[]):
        steps = []
        text_steps = []
        
        element_contains_text = False

        tag_selector = f"{element.name}"
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
            class_list = []
            class_selector = None
            for single_class in filtered_classes:
                class_list.append(single_class)
                class_selector = "." + ".".join(class_list)
                if SoupDomUtils.is_selector_unique(soup, f"{element.name}{class_selector}"):
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
                            # if is_selector_unique(soup, f"{element.name}{text_selector}"):
                            #     return f"{element.name}{text_selector}"
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
            parent_level = 0
            max_level = 10
            # Step 5: Parent and Sibling Relationships
            parent_selectors = []
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
                siblings = parent.find_all(element.name)
                if len(siblings) > 1:
                    index = siblings.index(element) + 1
                    return f"{''.join(steps)}:nth-of-type({index})"
        else:
            return ''.join(steps)