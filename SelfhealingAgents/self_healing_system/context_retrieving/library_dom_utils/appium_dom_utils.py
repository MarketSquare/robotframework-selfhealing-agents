import json
import re
from typing import Any, List, Optional

from robot.libraries.BuiltIn import BuiltIn
from bs4 import BeautifulSoup

from SelfhealingAgents.utils.logging import log
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils


class AppiumDomUtils(BaseDomUtils):
    """Appium library-specific DOM utility implementation.

    Provides DOM interaction methods tailored for Robot Framework's AppiumLibrary,
    including locator validation, uniqueness checks, DOM extraction, and locator metadata.

    Attributes:
        _library_instance: Instance of the AppiumLibrary used for DOM interactions.
    """
    def __init__(self):
        """Initializes AppiumDomUtils and retrieves the AppiumLibrary instance."""
        self._library_instance = BuiltIn().get_library_instance("AppiumLibrary")

    def is_locator_valid(self, locator: str) -> bool:
        """Checks if the locator is valid using AppiumLibrary methods.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is valid, False otherwise.
        """
        if self._library_instance is None:
            return True
        try:
            # Use dynamic attribute access to handle different AppiumLibrary versions
            if hasattr(self._library_instance, "get_webelements"):
                elements = getattr(self._library_instance, "get_webelements")(locator)
            else:
                return True  # Default to valid if method not found
            return len(elements) > 0
        except Exception:
            return False

    def is_locator_unique(self, locator: str) -> bool:
        """Checks if the locator uniquely identifies a single element.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is unique, False otherwise.
        """
        if self._library_instance is None:
            return True  # Skip validation if library is not available

        try:
            # Use dynamic attribute access to handle different AppiumLibrary versions
            if hasattr(self._library_instance, "get_webelements"):
                elements = getattr(self._library_instance, "get_webelements")(locator)
            else:
                return True  # Default to valid if method not found
            return len(elements) == 1
        except Exception:
            return False

    def get_dom_tree(self) -> str:
        """Retrieves the DOM tree using AppiumLibrary.

        For mobile applications, this returns the page source which contains the UI hierarchy in XML format.

        Returns:
            str: The DOM/UI tree as a string.
        """
        if self._library_instance is None:
            return "<hierarchy>AppiumLibrary not available</hierarchy>"

        def resolve_driver() -> Optional[Any]:
            driver = getattr(self._library_instance, "_current_application", None)
            if driver:
                return driver
            cache = getattr(self._library_instance, "_cache", None)
            if cache is not None:
                return getattr(cache, "current", None)
            return None

        def looks_like_session_error(source: str) -> bool:
            lowered = source.lower()
            return (
                source.lstrip().startswith("{")
                and (
                    "unable to find session" in lowered
                    or "invalid session id" in lowered
                    or "session id is null" in lowered
                )
            )

        def driver_page_source() -> Optional[str]:
            driver = resolve_driver()
            if driver is None:
                return None
            try:
                return driver.page_source
            except Exception:
                return None

        try:
            fetchers = [
                "get_source",
                "get_page_source",
            ]
            for fetcher in fetchers:
                if hasattr(self._library_instance, fetcher):
                    page_source = getattr(self._library_instance, fetcher)()
                    if isinstance(page_source, str) and not looks_like_session_error(page_source):
                        return page_source
                    fallback = driver_page_source()
                    if fallback:
                        return fallback
                    if isinstance(page_source, str):
                        return self._format_dom_error(page_source)
            fallback = driver_page_source()
            if fallback:
                return fallback
            return "<hierarchy>Unable to retrieve page source</hierarchy>"
        except Exception as exc:
            fallback = driver_page_source()
            if fallback:
                return fallback
            return f"<hierarchy>Error retrieving DOM tree: {str(exc)}"

    @staticmethod
    def _format_dom_error(raw: str) -> str:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return f"<hierarchy>Error retrieving DOM tree: {raw}</hierarchy>"

        message = (
            data.get("value", {}).get("message")
            or data.get("message")
            or raw
        )
        return f"<hierarchy>Error retrieving DOM tree: {message}</hierarchy>"

    def get_library_type(self) -> str:
        """Returns the library type identifier.

        Returns:
            str: The library type identifier ('appium').
        """
        return "appium"

    @log
    def get_locator_proposals(
        self, failed_locator: str, keyword_name: str
    ) -> list[str]:
        """Generates locator proposals for Appium.

        Produces XPath or attribute-based locators suitable for Android/iOS using
        attributes commonly present in Appium page source. Keeps proposals small
        and relies on runtime validation for uniqueness.

        Args:
            failed_locator: The locator that failed.
            keyword_name: The name of the keyword being executed.

        Returns:
            list[str]: Proposed locators in priority order.
        """
        proposals: List[str] = []

        def add_if(value: str | None) -> None:
            if value and value not in proposals:
                proposals.append(value)

        hints = self._parse_locator_hints(failed_locator)
        for text_hint in hints["text"]:
            literal = self._xpath_literal(text_hint)
            add_if(f"//*[@text={literal}]")
            add_if(f"//*[contains(@text,{literal})]")
        for desc_hint in hints["content_desc"]:
            literal = self._xpath_literal(desc_hint)
            add_if(f"//*[@content-desc={literal}]")
            add_if(f"//*[contains(@content-desc,{literal})]")
        for res_hint in hints["resource_id"]:
            literal = self._xpath_literal(res_hint)
            add_if(f"//*[@resource-id={literal}]")

        try:
            source: str = self.get_dom_tree()
            soup: BeautifulSoup = BeautifulSoup(source, "xml")
        except Exception:
            return proposals[:12]

        # Choose candidates based on keyword intent
        keyword_lower = str(keyword_name or "").lower()
        want_inputs: bool = keyword_lower in (
            "input text",
            "type text",
            "clear text",
            "press keys",
            "press key",
        )
        want_click: bool = "click" in keyword_lower or "tap" in keyword_lower

        # Iterate elements with attributes we can leverage
        for el in soup.find_all(True):
            attrs = el.attrs or {}
            tag = el.name or ""
            res_id = attrs.get("resource-id")
            content_desc = attrs.get("content-desc")
            text_value = attrs.get("text") or (el.get_text(strip=True) or None)
            name = attrs.get("name")
            label = attrs.get("label")
            value = attrs.get("value")
            klass = attrs.get("class") or attrs.get("className")

            # Heuristics for candidate relevance
            if want_inputs:
                if tag.endswith("EditText") or (klass and "EditText" in str(klass)) or (name and "TextField" in tag):
                    if res_id:
                        add_if(f"//*[@resource-id={self._xpath_literal(res_id)}]")
                    if content_desc:
                        add_if(f"//*[@content-desc={self._xpath_literal(content_desc)}]")
                    if text_value and tag:
                        literal = self._xpath_literal(text_value)
                        add_if(f"//{tag}[@text={literal}]")
                    if name and tag:
                        add_if(f"//{tag}[@name={self._xpath_literal(name)}]")
                    if label:
                        add_if(f"//*[@label={self._xpath_literal(label)}]")
                    if value:
                        add_if(f"//*[@value={self._xpath_literal(value)}]")
            elif want_click:
                clickable = attrs.get("clickable") == "true"
                is_buttonish = (
                    (tag and ("Button" in tag or "ImageButton" in tag))
                    or (klass and ("Button" in str(klass) or "ImageButton" in str(klass)))
                    or (label or name or content_desc)
                )
                if clickable or is_buttonish:
                    if res_id:
                        add_if(f"//*[@resource-id={self._xpath_literal(res_id)}]")
                    if content_desc:
                        literal = self._xpath_literal(content_desc)
                        add_if(f"//*[@content-desc={literal}]")
                        add_if(f"//*[contains(@content-desc,{literal})]")
                    if text_value and tag:
                        literal = self._xpath_literal(text_value)
                        add_if(f"//{tag}[@text={literal}]")
                        add_if(f"//*[contains(@text,{literal})]")
                    if label:
                        add_if(f"//*[@label={self._xpath_literal(label)}]")
                    if name:
                        add_if(f"//*[@name={self._xpath_literal(name)}]")
            else:
                # Generic: text-bearing elements
                if text_value:
                    literal = self._xpath_literal(text_value)
                    add_if(f"//*[@text={literal}]")
                    if len(text_value) <= 30:
                        add_if(f"//*[contains(@text,{literal})]")

            # Early stop to keep list small
            if len(proposals) >= 12:
                break

        # Fallback: if nothing found, suggest coarse XPath by class/tag
        if not proposals and soup and soup.find(True):
            first = soup.find(True)
            if first and first.name:
                proposals.append(f"//{first.name}")

        return proposals[:12]

    @staticmethod
    def _parse_locator_hints(locator: str) -> dict[str, List[str]]:
        hints: dict[str, List[str]] = {
            "text": [],
            "content_desc": [],
            "resource_id": [],
        }
        if not locator:
            return hints

        normalized = locator.strip()
        lower = normalized.lower()
        if lower.startswith("xpath=") or lower.startswith("xpath:"):
            normalized = normalized[6:]

        def collect(pattern: re.Pattern[str], bucket: list[str]) -> None:
            for value in pattern.findall(normalized):
                if value and value not in bucket:
                    bucket.append(value)

        collect(re.compile(r'@text\s*=\s*["\']([^"\']+)["\']'), hints["text"])
        collect(re.compile(r'contains\(@text\s*,\s*["\']([^"\']+)["\']\)'), hints["text"])

        collect(re.compile(r'@content-desc\s*=\s*["\']([^"\']+)["\']'), hints["content_desc"])
        collect(
            re.compile(r'contains\(@content-desc\s*,\s*["\']([^"\']+)["\']\)'),
            hints["content_desc"],
        )

        collect(re.compile(r'@resource-id\s*=\s*["\']([^"\']+)["\']'), hints["resource_id"])

        return hints

    @staticmethod
    def _xpath_literal(value: str) -> str:
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        concat_parts: List[str] = []
        for index, part in enumerate(parts):
            if part:
                concat_parts.append(f"'{part}'")
            if index != len(parts) - 1:
                concat_parts.append("\"'\"")
        return "concat(" + ", ".join(concat_parts) + ")"


    def is_element_clickable(self, locator: str) -> bool:
        """Checks if the element is clickable using AppiumLibrary.

        Heuristic using element attributes; returns False on errors.
        """
        if self._library_instance is None:
            return False
        try:
            if hasattr(self._library_instance, "get_webelements"):
                elements = getattr(self._library_instance, "get_webelements")(locator)
            else:
                return False
            if not elements:
                return False
            el = elements[0]
            # Visibility and enablement
            try:
                displayed = el.get_attribute("displayed") == "true" or bool(getattr(el, "is_displayed", lambda: False)())
            except Exception:
                displayed = False
            try:
                enabled = el.get_attribute("enabled") == "true" or bool(getattr(el, "is_enabled", lambda: False)())
            except Exception:
                enabled = False

            # Platform-specific hints
            klass = None
            try:
                klass = el.get_attribute("class")
            except Exception:
                pass
            tag_name = getattr(el, "tag_name", "") or ""
            is_buttonish = any(
                s in (klass or tag_name)
                for s in ["Button", "ImageButton", "CheckBox", "XCUIElementTypeButton", "XCUIElementTypeSwitch"]
            )
            try:
                clickable_attr = el.get_attribute("clickable") == "true"
            except Exception:
                clickable_attr = False

            return (displayed and enabled) and (clickable_attr or is_buttonish)
        except Exception:
            return False

    def get_locator_metadata(self, locator: str) -> list[dict]:
        """Retrieves metadata for the element(s) matching the given locator.

        Args:
            locator (str): The locator to get metadata for.

        Returns:
            List[Dict]: A list of dictionaries containing metadata about the matched elements.
        """
        if self._library_instance is None:
            return []

        try:
            # Try to get elements using Appium library methods
            if hasattr(self._library_instance, "get_webelements"):
                elements = getattr(self._library_instance, "get_webelements")(locator)
            else:
                return []

            metadata_list = []

            for element in elements:
                metadata = {}

                # Get basic element properties for mobile elements
                try:
                    metadata["tag"] = (
                        element.tag_name.lower() if hasattr(element, "tag_name") else ""
                    )
                except Exception:
                    metadata["tag"] = ""

                try:
                    metadata["resource_id"] = element.get_attribute("resource-id") or ""
                except Exception:
                    metadata["resource_id"] = ""

                try:
                    metadata["class"] = element.get_attribute("class") or ""
                except Exception:
                    metadata["class"] = ""

                try:
                    metadata["text"] = element.text or ""
                except Exception:
                    metadata["text"] = ""

                try:
                    metadata["content_desc"] = (
                        element.get_attribute("content-desc") or ""
                    )
                except Exception:
                    metadata["content_desc"] = ""

                try:
                    metadata["name"] = element.get_attribute("name") or ""
                except Exception:
                    metadata["name"] = ""

                try:
                    metadata["value"] = element.get_attribute("value") or ""
                except Exception:
                    metadata["value"] = ""

                try:
                    metadata["package"] = element.get_attribute("package") or ""
                except Exception:
                    metadata["package"] = ""

                try:
                    metadata["checkable"] = element.get_attribute("checkable") == "true"
                except Exception:
                    metadata["checkable"] = False

                try:
                    metadata["checked"] = element.get_attribute("checked") == "true"
                except Exception:
                    metadata["checked"] = False

                try:
                    metadata["clickable"] = element.get_attribute("clickable") == "true"
                except Exception:
                    metadata["clickable"] = False

                try:
                    metadata["enabled"] = element.get_attribute("enabled") == "true"
                except Exception:
                    metadata["enabled"] = False

                try:
                    metadata["focusable"] = element.get_attribute("focusable") == "true"
                except Exception:
                    metadata["focusable"] = False

                try:
                    metadata["focused"] = element.get_attribute("focused") == "true"
                except Exception:
                    metadata["focused"] = False

                try:
                    metadata["scrollable"] = (
                        element.get_attribute("scrollable") == "true"
                    )
                except Exception:
                    metadata["scrollable"] = False

                try:
                    metadata["selected"] = element.get_attribute("selected") == "true"
                except Exception:
                    metadata["selected"] = False

                try:
                    metadata["displayed"] = element.get_attribute("displayed") == "true"
                except Exception:
                    metadata["displayed"] = False

                metadata_list.append(metadata)

            return metadata_list

        except Exception:
            return []
