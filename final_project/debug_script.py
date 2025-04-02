import json
import os
from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods import posts

def get_wp_credentials():
    """Load WordPress credentials from JSON file"""
    try:
        # Look for credentials in the current directory and parent directory
        credential_paths = ['blog-credentials.json', '../blog-credentials.json']
        for path in credential_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        raise FileNotFoundError("Could not find blog-credentials.json")
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def main():
    # Get WordPress credentials
    credentials = get_wp_credentials()
    if not credentials:
        print("Failed to load WordPress credentials")
        return
    
    # Connect to WordPress
    try:
        wp_client = Client(credentials['xmlrpc_url'], credentials['username'], credentials['password'])
    except Exception as e:
        print(f"Error connecting to WordPress: {e}")
        return
    
    # Fetch recent posts
    try:
        recent_posts = wp_client.call(posts.GetPosts({'number': 3}))
        print(f"Type of recent_posts: {type(recent_posts)}")
        print(f"Length of recent_posts: {len(recent_posts)}")
        
        if recent_posts:
            first_post = recent_posts[0]
            print(f"Type of first post: {type(first_post)}")
            print(f"First post keys: {first_post.keys()}")
            print(f"First post title: {first_post.get('post_title', 'No title')}")
            print(f"First post content: {first_post.get('post_content', 'No content')[:100]}...")
    except Exception as e:
        print(f"Error fetching recent posts: {e}")

if __name__ == "__main__":
    main()
