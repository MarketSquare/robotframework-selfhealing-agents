import Browser
import pytest
from RobotAid.self_healing_system.context_retrieving.dom_robot_utils import RobotDomUtils
from RobotAid.self_healing_system.context_retrieving.dom_soap_utils import SoupDomUtils
from bs4 import BeautifulSoup

dom_tree = """
<html lang="en"
    	data-framework="react">
	<head>
		<meta charset="UTF-8">
			<meta name="description"
    				content="A TodoMVC written in React.">
				<meta name="viewport"
    					content="width=device-width,initial-scale=1">
					<meta http-equiv="X-UA-Compatible"
    						content="ie=edge">
						<title>TodoMVC: React</title>
						<script async=""
      							src="https://www.google-analytics.com/analytics.js"/>
						<script defer="defer"
      							src="app.bundle.js"/>
						<link href="app.css"
    							rel="stylesheet"></head>
						<body class="learn-bar">
							<aside class="learn">
								<header>
									<h3>React</h3>
									<span class="source-links">
										<h5>React</h5>
										<a href="https://github.com/tastejs/todomvc/tree/gh-pages/examples/react">Source</a>
										<h5>TypeScript + React</h5>
										<a class="demo-link"
 											data-type="local"
 											href="https://todomvc.com/examples/typescript-react">Demo</a>, <a href="https://github.com/tastejs/todomvc/tree/gh-pages/examples/typescript-react">Source</a>
									</span>
								</header>
								<hr>
									<blockquote class="quote speech-bubble">
										<p>React is a JavaScript library for creating user interfaces. Its core principles are declarative code, efficiency, and flexibility. Simply specify what your component looks like and React will keep it up-to-date when the underlying data changes.</p>
										<footer>
											<a href="http://facebook.github.io/react">React</a>
										</footer>
									</blockquote>
									<hr>
										<h4>Official Resources</h4>
										<ul>
											<li>
												<a href="https://react.dev/learn">Quick Start</a>
											</li>
											<li>
												<a href="https://react.dev/reference/react">API Reference</a>
											</li>
											<li>
												<a href="https://petehuntsposts.quora.com/React-Under-the-Hood">Philosophy</a>
											</li>
											<li>
												<a href="https://react.dev/community">React Community</a>
											</li>
										</ul>
										<h4>Community</h4>
										<ul>
											<li>
												<a href="https://stackoverflow.com/questions/tagged/reactjs">ReactJS on Stack Overflow</a>
											</li>
										</ul>
										<footer>
											<hr>
												<em>If you have other helpful links to share, or find any of the links above no longer work, please <a href="https://github.com/tastejs/todomvc/issues">let us know</a>.</em>
											</footer>
										</aside>
										<section class="todoapp"
       											id="root">
											<header class="header"
      												data-testid="header">
												<h1>todos</h1>
												<div class="input-container">
													<input class="new-todo"
     														id="todo-input"
     														type="text"
     														data-testid="text-input"
     														placeholder="What needs to be done?"
     														value="">
														<label class="visually-hidden"
     															for="todo-input">New Todo Input</label>
													</div>
												</header>
												<main class="main"
    													data-testid="main">
													<div class="toggle-all-container">
														<input class="toggle-all"
     															type="checkbox"
     															id="toggle-all"
     															data-testid="toggle-all">
															<label class="toggle-all-label"
     																for="toggle-all">Toggle All Input</label>
														</div>
														<ul class="todo-list"
  															data-testid="todo-list">
															<li class=""
  																data-testid="todo-item">
																<div class="view">
																	<input class="toggle"
     																		type="checkbox"
     																		data-testid="todo-item-toggle">
																		<label data-testid="todo-item-label">Learn Robot Framework</label>
																		<button class="destroy"
      																			data-testid="todo-item-button"/>
																	</div>
																</li>
																<li class=""
  																	data-testid="todo-item">
																	<div class="view">
																		<input class="toggle"
     																			type="checkbox"
     																			data-testid="todo-item-toggle">
																			<label data-testid="todo-item-label">Write Tests</label>
																			<button class="destroy"
      																				data-testid="todo-item-button"/>
																		</div>
																	</li>
																</ul>
															</main>
															<footer class="footer"
      																data-testid="footer">
																<span class="todo-count">2 items left!</span>
																<ul class="filters"
  																	data-testid="footer-navigation">
																	<li>
																		<a class="selected"
 																			href="#/">All</a>
																	</li>
																	<li>
																		<a class=""
 																			href="#/active">Active</a>
																	</li>
																	<li>
																		<a class=""
 																			href="#/completed">Completed</a>
																	</li>
																</ul>
																<button class="clear-completed"
      																	disabled="">Clear completed</button>
															</footer>
														</section>
														<footer class="info">
															<p>Double-click to edit a todo</p>
															<p>Created by the TodoMVC Team</p>
															<p>Part of <a href="http://todomvc.com">TodoMVC</a>
															</p>
														</footer>
														<script src="./base.js"/>
													</body>
												</html>
"""

@pytest.fixture()
def browser(tmpdir):
    Browser.Browser._output_dir = tmpdir
    browser = Browser.Browser()
    yield browser
    browser.close_browser("ALL")


def test_is_locator_unique(browser):
    dom_utils = RobotDomUtils(library_instance=browser)
    browser.new_page("https://playwright.dev/")

    locator = "h1"
    result = dom_utils.is_locator_unique(locator)
    
    # Assert: The locator should be unique
    assert result is True, f"Locator '{locator}' should be unique but was not."   

def test_is_locator_not_unique(browser):
    dom_utils = RobotDomUtils(library_instance=browser)
    browser.new_page("https://playwright.dev/")

    locator = "div"
    result = dom_utils.is_locator_unique(locator)
    
    # Assert: The locator should not be unique
    assert result is False, f"Locator '{locator}' should not be unique but was."

def test_is_locator_visible(browser):
    dom_utils = RobotDomUtils(library_instance=browser)
    browser.new_page("https://playwright.dev/")

    locator = "h1"
    result = dom_utils.is_locator_visible(locator)
    
    # Assert: The locator should be visible
    assert result is True, f"Locator '{locator}' should be visible but was not."

def test_generate_unique_css_selector():
    soup = BeautifulSoup(dom_tree, 'html.parser')
    element_types = ['a', 'button', 'checkbox', 'link', 'input', 'label', 'li']
    elements = soup.body.find_all(element_types)
    selectors = []
    for elem in elements:
        selector = SoupDomUtils.generate_unique_css_selector(elem, soup)
        selectors.append(selector)
    assert len(selectors) == len(elements), "The number of unique selectors should match the number of elements."
    expected_selectors = ['h5 + a:-soup-contains-own("Source")', 'a.demo-link', 'a.demo-link + a', 'p:-soup-contains-own("React is a JavaScript library for creating user interfaces. Its core principles are declarative code, efficiency, and flexibility. Simply specify what your component looks like and React will keep it up-to-date when the underlying data changes.") + footer a', 'li:-soup-contains("Quick Start")', 'a:-soup-contains-own("Quick Start")', 'li:-soup-contains("API Reference")', 'a:-soup-contains-own("API Reference")', 'li:-soup-contains("Philosophy")', 'a:-soup-contains-own("Philosophy")', 'li:-soup-contains("React Community")', 'a:-soup-contains-own("React Community")', 'li:-soup-contains("ReactJS on Stack Overflow")', 'a:-soup-contains-own("ReactJS on Stack Overflow")', 'a:-soup-contains-own("let us know")', 'input#todo-input', 'label:-soup-contains-own("New Todo Input")', 'input#toggle-all', 'label.toggle-all-label', 'li:-soup-contains("Learn Robot Framework")', 'input[type="checkbox"].toggle:has(+ label:-soup-contains-own("Learn Robot Framework"))', 'label:-soup-contains-own("Learn Robot Framework")', 'label:-soup-contains-own("Learn Robot Framework") + button.destroy', 'li:-soup-contains("Write Tests")', 'input[type="checkbox"].toggle:has(+ label:-soup-contains-own("Write Tests"))', 'label:-soup-contains-own("Write Tests")', 'label:-soup-contains-own("Write Tests") + button.destroy', 'li:-soup-contains("All")', 'a.selected', 'li:-soup-contains("Active")', 'a:-soup-contains-own("Active")', 'li:-soup-contains("Completed")', 'a:-soup-contains-own("Completed")', 'button.clear-completed', 'a:-soup-contains-own("TodoMVC")']
    assert selectors == expected_selectors, f"Generated selectors do not match the expected ones. Generated: {selectors}, Expected: {expected_selectors}"