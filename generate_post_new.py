import boto3
from datetime import datetime
import requests
import json
import re

AWS_REGION = "us-east-1"  # Replace with your AWS region
MODEL_ID = "anthropic.claude-v2"  # Bedrock Claude v2 model ID

def get_github_activity(username):
    """Fetch GitHub activity for inspiration"""
    headers = {'Accept': 'application/vnd.github.v3+json'}
    
    # Get user's starred repos
    stars_url = f'https://api.github.com/users/{username}/starred'
    stars_response = requests.get(stars_url, headers=headers)
    starred_repos = stars_response.json()[:5] if stars_response.status_code == 200 else []
    
    # Get user's recent commits
    events_url = f'https://api.github.com/users/{username}/events'
    events_response = requests.get(events_url, headers=headers)
    commit_events = [event for event in (events_response.json() if events_response.status_code == 200 else [])
                    if event['type'] == 'PushEvent'][:5]
    
    # Format the activity data
    activities = {
        'starred_repos': [{'name': repo['name'], 'description': repo['description']} 
                         for repo in starred_repos],
        'recent_commits': [{'repo': event['repo']['name'], 
                          'message': event['payload']['commits'][0]['message']}
                         for event in commit_events if 'commits' in event['payload'] and event['payload']['commits']]
    }
    
    return activities

def generate_post_with_bedrock(github_activity):
    """Generate a new SEO-optimized post using Amazon Bedrock's Claude model"""
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION
    )
    
    # Format GitHub activity for the prompt
    starred_repos = "\n".join([f"- {repo['name']}: {repo['description']}" 
                             for repo in github_activity['starred_repos']])
    recent_commits = "\n".join([f"- In {commit['repo']}: {commit['message']}" 
                             for commit in github_activity['recent_commits']])
    
    prompt = f"""
Write a witty, sarcastic blog post in the style of a stand-up comedian who's been burned by Kubernetes before.
The post should be structured in exactly 6 paragraphs:

1. Start with a personal anecdote related to tech (preferably involving one of these recent GitHub interactions):
Recent GitHub Activity:
Starred Repositories:
{starred_repos}

Recent Commits:
{recent_commits}

2. Build up the story with your frustrations and challenges
3. Share the "aha moment" or the lesson learned
4. Relate it to broader tech industry trends
5. Share practical advice (while maintaining the sarcastic tone)
6. End with a strong call-to-action that encourages reader engagement

The post should:
1. Maintain a consistently witty and sarcastic tone throughout
2. Include tech-specific humor and references
3. Have relatable developer pain points
4. Include ONE image placeholder near the beginning using format [IMAGE: detailed description]
5. Be engaging and conversational
6. Include proper H2 and H3 subheadings
7. Be 800-1200 words

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

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4000,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response.get('body').read())
        generated_text = response_body.get('content', '')
        
        try:
            post_data = json.loads(generated_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
                post_data = json.loads(json_str)
            else:
                raise ValueError("No JSON object found in response")
        
        if "content" in post_data:
            content = post_data["content"]
            if content.strip().startswith('{') and content.strip().endswith('}'):
                try:
                    content_json = json.loads(content)
                    if "content" in content_json:
                        post_data["content"] = content_json["content"]
                except:
                    pass
            
            post_data["content"] = post_data["content"].replace(
                "[IMAGE:", 
                "<div class='image-suggestion'><em>Suggested image here: "
            ).replace("]", "</em></div>")
            
            post_data["content"] = re.sub(
                r'\[Image: (.*?)\]',
                r"<div class='image-suggestion'><em>Suggested image here: \1</em></div>",
                post_data["content"]
            )
            
            return post_data
            
    except Exception as e:
        print(f"Error generating post: {str(e)}")
        return None

def main():
    # Get GitHub activity
    github_username = "felipedbene"
    github_activity = get_github_activity(github_username)
    
    # Generate the post
    post_data = generate_post_with_bedrock(github_activity)
    
    if post_data:
        print("\nGenerated Blog Post:")
        print("===================")
        print(f"Title: {post_data.get('title', 'No title')}")
        print(f"Focus Keyphrase: {post_data.get('focus_keyphrase', 'No keyphrase')}")
        print(f"Tags: {', '.join(post_data.get('tags', ['No tags']))}")
        print("\nContent Preview (first 500 chars):")
        print(f"{post_data.get('content', 'No content')[:500]}...")
    else:
        print("Failed to generate blog post")

if __name__ == "__main__":
    main()