from hallmonitor.hmutils import CombinationRow


def test_combination_row_initialization():
    name = "TestCombination"
    variables = ["var1", "var2", "var3"]

    comb_row = CombinationRow(name=name, variables=variables)

    # Check if the name and variables are correctly assigned
    assert comb_row.name == name
    assert comb_row.variables == variables


def test_combination_row_empty_variables():
    name = "EmptyCombination"
    variables = []

    comb_row = CombinationRow(name=name, variables=variables)

    # Check that the name is correctly assigned and variables is an empty list
    assert comb_row.name == name
    assert comb_row.variables == []


def test_combination_row_attribute_access():
    name = "AccessTest"
    variables = ["varA", "varB"]

    comb_row = CombinationRow(name=name, variables=variables)

    # Access and assert the attributes
    assert comb_row.name == "AccessTest"
    assert comb_row.variables == ["varA", "varB"]


def test_combination_row_equality():
    row1 = CombinationRow(name="EqualTest", variables=["a", "b"])
    row2 = CombinationRow(name="EqualTest", variables=["a", "b"])

    # Check if both instances are considered equal
    assert row1 == row2
