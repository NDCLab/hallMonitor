import pytest

from hallmonitor.hmutils import get_unique_sub_ses_run


# Mock Identifier class for testing
class MockIdentifier:
    def __init__(self, subject, session, run=None):
        self.subject = subject
        self.session = session
        self.run = run

    def __str__(self):
        return f"{self.subject}_{self.session}_{self.run}"

    @classmethod
    def from_str(cls, identifier_str):
        parts = identifier_str.split("_")
        print(parts)
        if len(parts) != 3:
            raise ValueError(f"Invalid identifier format: {identifier_str}")
        return cls(subject=parts[0], session=parts[1], run=parts[2])


@pytest.fixture
def mock_identifier():
    # Mock the Identifier class for testing
    return MockIdentifier


@pytest.mark.parametrize(
    "identifiers, expected",
    [
        # Case: Valid strings parsed into unique subject-session pairs
        (
            ["sub1_ses1_r1", "sub2_ses1_r1", "sub1_ses1_r1"],
            [("sub1", "ses1", "r1"), ("sub2", "ses1", "r1")],
        ),
        # Case: Unique subject-session pairs from Identifier objects
        (
            [
                MockIdentifier(subject="sub1", session="ses1", run="r1"),
                MockIdentifier(subject="sub2", session="ses1", run="r1"),
                MockIdentifier(subject="sub1", session="ses1", run="r1"),
            ],
            [("sub1", "ses1", "r1"), ("sub2", "ses1", "r1")],
        ),
        # Case: Mixed subjects and sessions
        (
            ["sub1_ses1_r1", "sub1_ses2_r1", "sub2_ses1_r1"],
            [("sub1", "ses1", "r1"), ("sub1", "ses2", "r1"), ("sub2", "ses1", "r1")],
        ),
        # Case: Identifiers already unique, no duplicates
        (
            ["sub1_ses1_r1", "sub3_ses3_r1"],
            [("sub1", "ses1", "r1"), ("sub3", "ses3", "r1")],
        ),
    ],
)
def test_get_unique_sub_ses_run(identifiers, expected, mock_identifier, monkeypatch):
    monkeypatch.setattr("hallmonitor.hmutils.Identifier", mock_identifier)

    result = get_unique_sub_ses_run(identifiers)
    assert sorted(result) == sorted(expected)


def test_get_unique_sub_ses_run_invalid_format(monkeypatch, mock_identifier):
    # Patch Identifier to use the mock
    monkeypatch.setattr("hallmonitor.hmutils.Identifier", mock_identifier)

    # Identifiers with invalid formats (too many or too few parts)
    with pytest.raises(ValueError, match="Could not build Identifier"):
        get_unique_sub_ses_run(["sub1ses1run1"])  # Missing delimiter

    with pytest.raises(ValueError, match="Could not build Identifier"):
        get_unique_sub_ses_run(["sub1_ses1_run1_extra"])  # Too many parts

    with pytest.raises(ValueError, match="Could not build Identifier"):
        get_unique_sub_ses_run(["sub1_ses1"])  # Not enough parts


def test_get_unique_sub_ses_run_mixed_types(monkeypatch, mock_identifier):
    monkeypatch.setattr("hallmonitor.hmutils.Identifier", mock_identifier)

    # Mixed list of strings and Identifier objects
    identifiers = [
        "sub1_ses1_r1",
        mock_identifier("sub2", "ses2", "r1"),
        mock_identifier("sub1", "ses1", "r1"),
    ]
    result = get_unique_sub_ses_run(identifiers)
    assert sorted(result) == [("sub1", "ses1", "r1"), ("sub2", "ses2", "r1")]


def test_get_unique_sub_ses_run_already_unique(monkeypatch, mock_identifier):
    monkeypatch.setattr("hallmonitor.hmutils.Identifier", mock_identifier)

    identifiers = ["sub1_ses1_r1", "sub2_ses2_r1", "sub3_ses3_r1"]
    result = get_unique_sub_ses_run(identifiers)
    assert sorted(result) == [
        ("sub1", "ses1", "r1"),
        ("sub2", "ses2", "r1"),
        ("sub3", "ses3", "r1"),
    ]


def test_get_unique_sub_ses_run_empty_list():
    # Case: Empty list should return an empty list
    result = get_unique_sub_ses_run([])
    assert result == []
