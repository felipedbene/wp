#!/usr/bin/env python3
"""
Script to fix JSON handling in the WordPress post generator
"""

import json
import re

def extract_content_from_json(json_text):
    """
    Extract just the content field from JSON response
    """
    try:
        # Try to parse the entire text as JSON
        data = json.loads(json_text)
        if "content" in data:
            return data["content"]
        return json_text
    except json.JSONDecodeError:
        # If not valid JSON, try to extract JSON object
        json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                if "content" in data:
                    return data["content"]
            except:
                pass
        
        # If all else fails, return the original text
        return json_text

# Test with some sample JSON responses
test_cases = [
    '{"title": "Test Post", "content": "<p>This is the actual content</p>", "tags": ["test"]}',
    'Some text before {"title": "Test Post", "content": "<p>This is the actual content</p>"} some text after',
    '<p>Not JSON at all</p>'
]

print("Testing JSON content extraction:")
for i, test in enumerate(test_cases):
    print(f"\nTest case {i+1}:")
    print(f"Input: {test[:50]}..." if len(test) > 50 else f"Input: {test}")
    result = extract_content_from_json(test)
    print(f"Output: {result[:50]}..." if len(result) > 50 else f"Output: {result}")
