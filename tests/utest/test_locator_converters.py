from RobotAid.self_healing_system.reponse_converters import convert_response_to_list, convert_response_to_dict, extract_json_objects

def test_convert_response_to_list() -> None:
    """Test the conversion of a response string to a list of strings."""
    response = '[\"locator1\", \"locator2\", \"locator3\"]'
    result = convert_response_to_list(response)
    assert result == ["locator1", "locator2", "locator3"]

def test_convert_response_to_list_empty() -> None:
    """Test the conversion of an empty response string to a list."""
    response = '[]'
    result = convert_response_to_list(response)
    assert result == []

def test_convert_response_to_list_invalid() -> None:
    """Test the conversion of an invalid response string to a list."""
    response = '[\"locator1\", \"locator2\", \"locator3\"'
    result = convert_response_to_list(response)
    assert result == []

def test_convert_response_to_dict() -> None:
    """Test the conversion of a response string to a dictionary."""
    response = '{"locator1": "value1", "locator2": "value2"}'
    result = convert_response_to_dict(response)
    assert result == {"locator1": "value1", "locator2": "value2"}
