#!/usr/bin/env python3
"""
Unit tests for forumTitle and blogTitle field assignment.
These tests verify that the correct field is used based on item type.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import (
    prepare_substack_item_update,
    prepare_linkedin_item_update,
    validate_item_fields,
)


def test_forumpost_uses_forumtitle():
    """Test that forumPost items use forumTitle field"""
    # Mock item
    item = {"data": {"creators": [], "tags": [], "url": "https://example.com"}}

    # Metadata indicating a forum post (Comment type)
    metadata = {
        "type": "Comment",
        "title": "Test Comment",
        "author": "Test Author",
        "date": "2024-01-01",
        "publisher": "Test Forum",
    }

    # Test Substack
    result = prepare_substack_item_update(item, metadata)
    assert (
        result["itemType"] == "forumPost"
    ), f"Expected forumPost, got {result['itemType']}"
    assert "forumTitle" in result, "forumTitle should be set for forumPost"
    assert (
        result["forumTitle"] == "Test Forum"
    ), f"Expected 'Test Forum', got {result.get('forumTitle')}"
    assert "blogTitle" not in result, "blogTitle should NOT be set for forumPost"
    print("✅ Substack forumPost correctly uses forumTitle")

    # Test LinkedIn
    result = prepare_linkedin_item_update(item, metadata)
    assert (
        result["itemType"] == "forumPost"
    ), f"Expected forumPost, got {result['itemType']}"
    assert "forumTitle" in result, "forumTitle should be set for forumPost"
    assert (
        result["forumTitle"] == "Test Forum"
    ), f"Expected 'Test Forum', got {result.get('forumTitle')}"
    assert "blogTitle" not in result, "blogTitle should NOT be set for forumPost"
    print("✅ LinkedIn forumPost correctly uses forumTitle")


def test_blogpost_uses_blogtitle():
    """Test that blogPost items use blogTitle field"""
    # Mock item
    item = {"data": {"creators": [], "tags": [], "url": "https://example.com"}}

    # Metadata indicating a blog post (Article type)
    metadata = {
        "type": "Article",
        "title": "Test Article",
        "author": "Test Author",
        "date": "2024-01-01",
        "publisher": "Test Blog",
    }

    # Test Substack
    result = prepare_substack_item_update(item, metadata)
    assert (
        result["itemType"] == "blogPost"
    ), f"Expected blogPost, got {result['itemType']}"
    assert "blogTitle" in result, "blogTitle should be set for blogPost"
    assert (
        result["blogTitle"] == "Test Blog"
    ), f"Expected 'Test Blog', got {result.get('blogTitle')}"
    assert "forumTitle" not in result, "forumTitle should NOT be set for blogPost"
    print("✅ Substack blogPost correctly uses blogTitle")

    # Test LinkedIn
    result = prepare_linkedin_item_update(item, metadata)
    assert (
        result["itemType"] == "blogPost"
    ), f"Expected blogPost, got {result['itemType']}"
    assert "blogTitle" in result, "blogTitle should be set for blogPost"
    assert (
        result["blogTitle"] == "Test Blog"
    ), f"Expected 'Test Blog', got {result.get('blogTitle')}"
    assert "forumTitle" not in result, "forumTitle should NOT be set for blogPost"
    print("✅ LinkedIn blogPost correctly uses blogTitle")


def test_validate_item_fields():
    """Test the validate_item_fields function"""
    # Test forumPost with blogTitle (should be removed)
    data = {
        "itemType": "forumPost",
        "forumTitle": "Test Forum",
        "blogTitle": "Should Be Removed",
    }
    result = validate_item_fields(data)
    assert "forumTitle" in result, "forumTitle should be preserved"
    assert "blogTitle" not in result, "blogTitle should be removed from forumPost"
    print("✅ Validation correctly removes blogTitle from forumPost")

    # Test blogPost with forumTitle (should be removed)
    data = {
        "itemType": "blogPost",
        "blogTitle": "Test Blog",
        "forumTitle": "Should Be Removed",
    }
    result = validate_item_fields(data)
    assert "blogTitle" in result, "blogTitle should be preserved"
    assert "forumTitle" not in result, "forumTitle should be removed from blogPost"
    print("✅ Validation correctly removes forumTitle from blogPost")


def test_forum_type_mappings():
    """Test that Comment, DiscussionForumPosting, and SocialMediaPosting map to forumPost"""
    item = {"data": {"creators": [], "tags": [], "url": "https://example.com"}}

    forum_types = ["Comment", "DiscussionForumPosting", "SocialMediaPosting"]

    for json_ld_type in forum_types:
        metadata = {
            "type": json_ld_type,
            "title": "Test",
            "author": "Author",
            "date": "2024-01-01",
            "publisher": "Publisher",
        }

        # Test Substack
        result = prepare_substack_item_update(item, metadata)
        assert (
            result["itemType"] == "forumPost"
        ), f"{json_ld_type} should map to forumPost, got {result['itemType']}"
        assert "forumTitle" in result, f"{json_ld_type} should have forumTitle"
        assert "blogTitle" not in result, f"{json_ld_type} should NOT have blogTitle"

        # Test LinkedIn
        result = prepare_linkedin_item_update(item, metadata)
        assert (
            result["itemType"] == "forumPost"
        ), f"{json_ld_type} should map to forumPost, got {result['itemType']}"
        assert "forumTitle" in result, f"{json_ld_type} should have forumTitle"
        assert "blogTitle" not in result, f"{json_ld_type} should NOT have blogTitle"

        print(f"✅ {json_ld_type} correctly maps to forumPost with forumTitle")


def test_blog_type_mappings():
    """Test that other types map to blogPost"""
    item = {"data": {"creators": [], "tags": [], "url": "https://example.com"}}

    blog_types = ["Article", "BlogPosting", "NewsArticle", None]

    for json_ld_type in blog_types:
        metadata = {
            "type": json_ld_type,
            "title": "Test",
            "author": "Author",
            "date": "2024-01-01",
            "publisher": "Publisher",
        }

        # Test Substack
        result = prepare_substack_item_update(item, metadata)
        assert (
            result["itemType"] == "blogPost"
        ), f"{json_ld_type} should map to blogPost, got {result['itemType']}"
        assert "blogTitle" in result, f"{json_ld_type} should have blogTitle"
        assert "forumTitle" not in result, f"{json_ld_type} should NOT have forumTitle"

        # Test LinkedIn
        result = prepare_linkedin_item_update(item, metadata)
        assert (
            result["itemType"] == "blogPost"
        ), f"{json_ld_type} should map to blogPost, got {result['itemType']}"
        assert "blogTitle" in result, f"{json_ld_type} should have blogTitle"
        assert "forumTitle" not in result, f"{json_ld_type} should NOT have forumTitle"

        print(f"✅ {json_ld_type or 'None'} correctly maps to blogPost with blogTitle")


if __name__ == "__main__":
    print("Running field assignment tests...\n")
    test_forumpost_uses_forumtitle()
    test_blogpost_uses_blogtitle()
    test_validate_item_fields()
    print("\nTesting type mappings...\n")
    test_forum_type_mappings()
    print()
    test_blog_type_mappings()
    print("\n✨ All tests passed!")
