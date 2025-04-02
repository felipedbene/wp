#!/usr/bin/env python3
"""
Script to fix JSON content issues in WordPress post generator
"""

import json
import re
import boto3
import requests
from datetime import datetime

# AWS configuration
AWS_REGION = "us-west-2"
MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Claude 3.5 Sonnet v2

def generate_post_with_bedrock(prompt_text):
    """Generate a post using Amazon Bedrock's Claude model with improved JSON handling"""
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION
    )
    
    # Call Bedrock with Claude
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4000,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": prompt_text
            }
        ]
    }
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response.get('body').read())
        generated_text = response_body.get('content')[0].get('text')
        
        # Print the raw response for debugging
        print("Raw response from Claude (first 200 chars):")
        print(generated_text[:200] + "...")
        
        # Extract the JSON from the response
        try:
            # First, try to parse the entire response as JSON
            try:
                post_data = json.loads(generated_text)
                print("Successfully parsed complete JSON response")
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text
                print("Failed to parse complete response as JSON, trying to extract JSON object...")
                json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    # Replace any control characters that might be causing issues
                    json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
                    post_data = json.loads(json_str)
                    print("Successfully extracted and parsed JSON object")
                else:
                    raise ValueError("No JSON object found in response")
            
            # Verify that the content field doesn't contain JSON
            if "content" in post_data:
                content = post_data["content"]
                
                # Check if content appears to contain JSON
                if content.strip().startswith('{') and '}' in content:
                    print("WARNING: Content field appears to contain JSON. Attempting to extract actual content...")
                    try:
                        # Try to parse the content as JSON and extract its content field
                        content_json = json.loads(content)
                        if "content" in content_json:
                            post_data["content"] = content_json["content"]
                            print("Successfully extracted nested content")
                    except:
                        print("Failed to extract nested content, using as is")
                
                # Process image placeholders
                post_data["content"] = post_data["content"].replace(
                    "[IMAGE:", 
                    "<div class='image-suggestion'><em>Suggested image here: "
                ).replace("]", "</em></div>")
            
            return post_data
                
        except Exception as e:
            print(f"Error parsing Claude's response: {e}")
            print(f"Raw response: {generated_text[:500]}...")
            
            # Create a simple fallback post
            return {
                "title": "New Blog Post",
                "content": "<p>Failed to generate proper content. Please try again.</p>",
                "tags": ["blog", "thoughts"],
                "meta_description": "Read our latest blog post with insights and reflections.",
                "excerpt": "A new post sharing thoughts and insights.",
                "focus_keyphrase": "blog post",
                "category_suggestion": "Blog",
                "image_alt_template": "Image related to blog post"
            }
            
    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return None

# Test with a simple prompt
test_prompt = """
Write a fun, engaging blog post about WordPress.

Format your response as valid JSON with these fields:
- "title": SEO title (under 60 chars)
- "focus_keyphrase": 2-4 word phrase
- "meta_description": Under 160 chars
- "content": HTML formatted post (IMPORTANT: Do not include any JSON syntax in the content field)
- "tags": 5-8 relevant tags
- "excerpt": Short excerpt
- "category_suggestion": Category
- "image_alt_template": Template for image alt text
"""

print("Testing improved JSON content handling...")
result = generate_post_with_bedrock(test_prompt)

if result:
    print("\nGenerated post:")
    print(f"Title: {result.get('title', 'No title')}")
    print(f"Focus keyphrase: {result.get('focus_keyphrase', 'No focus keyphrase')}")
    
    # Check if content contains JSON
    content = result.get('content', '')
    if content.strip().startswith('{') and '}' in content:
        print("\nWARNING: Content still contains JSON!")
        print(f"Content preview: {content[:200]}...")
    else:
        print("\nContent looks good (no JSON detected)")
        print(f"Content preview: {content[:200]}...")
else:
    print("Failed to generate post")
