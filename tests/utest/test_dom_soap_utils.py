import sys
import types
import pytest
import importlib
from bs4 import BeautifulSoup, Tag
from typing import Any, Callable, Tuple


MODULE_PATH: str = "SelfhealingAgents.self_healing_system.context_retrieving.dom_soap_utils"


def _install_stub_logging_if_needed() -> None:
    try:
        import SelfhealingAgents
        return
    except Exception:
        pass
    pkg = types.ModuleType("SelfhealingAgents")
    pkg.__path__ = []
    utils = types.ModuleType("SelfhealingAgents.utils")
    utils.__path__ = []
    logging_mod = types.ModuleType("SelfhealingAgents.utils.logging")
    def log(func: Callable[..., Any]) -> Callable[..., Any]:
        return func
    logging_mod.log = log
    sys.modules["SelfhealingAgents"] = pkg
    sys.modules["SelfhealingAgents.utils"] = utils
    sys.modules["SelfhealingAgents.utils.logging"] = logging_mod


def _import_module_fresh() -> Any:
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]
    return importlib.import_module(MODULE_PATH)


@pytest.fixture(scope="module")
def soupdom() -> Tuple[Any, Any]:
    _install_stub_logging_if_needed()
    mod = _import_module_fresh()
    return mod, getattr(mod, "SoupDomUtils")


def _sample_html() -> str:
    return """
    <html>
      <head>
        <script>var x = 1;</script>
      </head>
      <body>
        <nav>main nav</nav>
        <div id="main">
          <ul id="list">
            <li><div class="item">First</div></li>
            <li><div class="item">Second</div></li>
          </ul>
          <p id="p1">Hello <b>world</b></p>
          <p id="p2">Just text</p>
          <div id="d1" class="hidden-panel">Hidden</div>
          <div id="d2" class="visible item" role="button" name="go" type="button" placeholder="ph">Click me</div>
          <a href="/x" class="link">A</a>
          <picture class="pic"></picture>
          <img class="im" alt="desc" src="x.jpg" />
          <section class="sec" style="color:red"><span style="display: none">hide</span></section>
          <dialog id="dlg"><span id="in-dlg">Inside</span></dialog>
          <dialog id="dlg2" open><span id="in-dlg-open">Open</span></dialog>
          <input type="hidden" value="secret" />
        </div>
        <svg><g></g></svg>
        <template><div>t</div></template>
      </body>
    </html>
    """


@pytest.fixture()
def soup() -> BeautifulSoup:
    return BeautifulSoup(_sample_html(), "html.parser")


def test_clean_text_for_selector(soupdom: Tuple[Any, Any]) -> None:
    _, S = soupdom
    out: str = S.clean_text_for_selector("  Hello   world\nagain\t ")
    assert out == "Hello world again"


def test_get_selector_count_and_invalid(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    assert S.get_selector_count(soup, "div.item") == 3
    assert S.get_selector_count(soup, "div#d2") == 1
    assert S.get_selector_count(soup, "div[") == 0


def test_is_selector_unique(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    assert S.is_selector_unique(soup, "p#p2") is True
    assert S.is_selector_unique(soup, "div.item") is False
    assert S.is_selector_unique(soup, "?? invalid ??") is False


def test_has_child_dialog_without_open_true_false(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    container: Tag = soup.select_one("#main")
    assert S.has_child_dialog_without_open(container) is True
    open_dlg: Tag = soup.select_one("#dlg2")
    assert S.has_child_dialog_without_open(open_dlg) is False


def test_is_headline_and_others(soupdom: Tuple[Any, Any]) -> None:
    _, S = soupdom
    h = BeautifulSoup("<h3>t</h3>", "html.parser").h3
    d = BeautifulSoup("<div>t</div>", "html.parser").div
    assert S.is_headline(h) is True
    assert S.is_headline(d) is False


def test_is_div_in_li(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    div_in_li: Tag = soup.select_one("ul#list li div")
    lone_div: Tag = soup.select_one("#d2")
    assert S.is_div_in_li(div_in_li) is True
    assert S.is_div_in_li(lone_div) is False


def test_is_p(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    p1: Tag = soup.select_one("#p1")
    d2: Tag = soup.select_one("#d2")
    assert S.is_p(p1) is True
    assert S.is_p(d2) is False


def test_has_parent_dialog_without_open(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    inside_closed: Tag = soup.select_one("#in-dlg")
    inside_open: Tag = soup.select_one("#in-dlg-open")
    assert S.has_parent_dialog_without_open(inside_closed) is True
    assert S.has_parent_dialog_without_open(inside_open) is False


def test_is_leaf_or_lowest(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    p2: Tag = soup.select_one("#p2")
    p1: Tag = soup.select_one("#p1")
    main_div: Tag = soup.select_one("#main")
    assert S.is_leaf_or_lowest(p2) is True
    assert S.is_leaf_or_lowest(p1) is True
    assert S.is_leaf_or_lowest(main_div) is False


def test_has_direct_text(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    p2: Tag = soup.select_one("#p2")
    p1: Tag = soup.select_one("#p1")
    assert S.has_direct_text(p2) is True
    assert S.has_direct_text(p1) is False


def test_generate_unique_css_selector_by_id(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    d2: Tag = soup.select_one("#d2")
    sel: str | None = S.generate_unique_css_selector(d2, soup)
    assert sel == "div#d2"


def test_generate_unique_css_selector_by_text_own(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    p2: Tag = soup.select_one("#p2")
    sel: str | None = S.generate_unique_css_selector(p2, soup)
    assert sel in {"p#p2", 'p:-soup-contains-own("Just text")', 'p:-soup-contains("Just text")'}


def test_generate_unique_css_selector_non_unique_when_allowed(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    item: Tag = soup.select("div.item")[0]
    sel: str | None = S.generate_unique_css_selector(item, soup, only_return_unique_selectors=False)
    assert sel in {"div.item", 'div.item:-soup-contains-own("First")', 'div.item:-soup-contains("First")'}


def test_generate_unique_css_selector_nth_of_type_fallback(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    item: Tag = soup.select("div.item")[0]
    sel: str | None = S.generate_unique_css_selector(item, soup, only_return_unique_selectors=True)
    assert sel is not None
    assert sel.startswith("div")
    assert (":nth-of-type(" in sel) or (":-soup-contains" in sel)


def test_has_display_none(soupdom: Tuple[Any, Any]) -> None:
    _, S = soupdom
    tag: Tag = BeautifulSoup('<span style="color:red; display: none">x</span>', "html.parser").span
    assert S.has_display_none(tag) is True


def test_get_simplified_dom_tree_removes_noise(soupdom: Tuple[Any, Any]) -> None:
    _, S = soupdom
    src: str = _sample_html()
    simplified: str | None = S.get_simplified_dom_tree(src)
    assert simplified is not None
    assert "<script" not in simplified
    assert "<svg" not in simplified
    assert "<template" not in simplified
    assert "<nav" not in simplified
    assert 'href="' not in simplified
    assert 'style="' not in simplified
    assert 'type="hidden"' not in simplified
    assert "<body" in simplified or simplified.startswith("<body")
    dom: BeautifulSoup = BeautifulSoup(simplified, "html.parser")
    for t in ["a", "picture", "img", "section"]:
        assert all("class" not in node.attrs for node in dom.find_all(t))


def test_is_xpath_unique_and_multiple(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    assert S.is_xpath_unique(soup, "//p[@id='p2']") is True
    assert S.is_xpath_multiple(soup, "//div[@class='item']") is True
    assert S.is_xpath_unique(soup, "//*[") is False


def test_generate_unique_xpath_selector_by_id(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    p2: Tag = soup.select_one("#p2")
    xp: str | None = S.generate_unique_xpath_selector(p2, soup)
    assert xp in {"//p[@id='p2']", "//p[contains(text(), 'Just text')]", "//*[contains(text(), 'Just text')]"}


def test_generate_unique_xpath_selector_by_text(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    d2: Tag = soup.select_one("#d2")
    xp: str | None = S.generate_unique_xpath_selector(d2, soup, check_text=True)
    assert xp in {"//div[contains(text(), 'Click me')]", "//*[contains(text(), 'Click me')]"}


def test_generate_unique_xpath_selector_none_returns_empty(soupdom: Tuple[Any, Any], soup: BeautifulSoup) -> None:
    _, S = soupdom
    xp: str | None = S.generate_unique_xpath_selector(None, soup)
    assert xp == ""


def test_clean_text_for_xpath(soupdom: Tuple[Any, Any]) -> None:
    _, S = soupdom
    out: str = S.clean_text_for_xpath("  Click   me \n now ")
    assert out == "Click me now"
