import pytest
from pydantic import ValidationError

from app.schemas.document import DocumentCreate


def test_tags_are_deduped_lowercased_and_sorted():
    doc = DocumentCreate(title="T", content="C", tags=["Python", "python", " ML "])
    assert doc.tags == ["ml", "python"]


def test_blank_title_rejected():
    with pytest.raises(ValidationError):
        DocumentCreate(title="   ", content="C")


def test_blank_content_rejected():
    with pytest.raises(ValidationError):
        DocumentCreate(title="T", content="   ")


def test_negative_popularity_rejected():
    with pytest.raises(ValidationError):
        DocumentCreate(title="T", content="C", popularity=-1.0)


def test_title_too_long_rejected():
    with pytest.raises(ValidationError):
        DocumentCreate(title="x" * 600, content="C")


def test_defaults_applied():
    doc = DocumentCreate(title="T", content="C")
    assert doc.language == "en"
    assert doc.tags == []
    assert doc.popularity == 0.0
    assert doc.doc_metadata == {}
