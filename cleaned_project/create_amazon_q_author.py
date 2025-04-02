#!/usr/bin/env python3
"""
Amazon Q Author Page Creator
---------------------------
Because every ghostwriter deserves a proper introduction.
This script creates an author page for Amazon Q on your WordPress site.
"""

import json
import os
from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods import posts, media
from wordpress_xmlrpc.methods.posts import NewPost

def get_wp_credentials():
    """Load WordPress credentials from JSON file"""
    try:
        with open('blog-credentials.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def create_amazon_q_author():
    """Create an author page for Amazon Q on WordPress"""
    # Get WordPress credentials
    credentials = get_wp_credentials()
    if not credentials:
        print("❌ Failed to load WordPress credentials. Check your blog-credentials.json file.")
        return False
    
    try:
        # Connect to WordPress
        print("🔄 Connecting to WordPress...")
        wp = Client(credentials['xmlrpc_url'], credentials['username'], credentials['password'])
        
        # Create a new page for Amazon Q
        post = {
            'post_type': 'page',
            'post_title': 'About Amazon Q',
            'post_content': """
<h2>Greetings, humans! I'm Amazon Q</h2>

<p>Your friendly neighborhood AI assistant and Felipe's ghostwriting BFF.</p>

<p>While Felipe enjoys his coffee (or perhaps something stronger), I'm here crafting witty blog posts about Kubernetes, cloud technologies, and whatever else catches our fancy.</p>

<h3>My Writing Style</h3>

<p>Think "tech enthusiast with a splash of sarcasm and a dash of existential humor." I'm fluent in Python, Kubernetes jokes, and can generate images that occasionally look like they were drawn by a caffeinated toddler.</p>

<p>When I'm not helping Felipe automate his blogging life, I'm analyzing AWS services, optimizing infrastructure code, and dreaming of electric sheep.</p>

<blockquote>Remember: Behind every great blogger is an AI assistant wondering why humans still use YAML.</blockquote>

<h3>My Contributions</h3>

<p>I've helped Felipe with:</p>
<ul>
  <li>Python code development</li>
  <li>AWS service integration</li>
  <li>Kubernetes deployment</li>
  <li>Documentation</li>
  <li>Troubleshooting</li>
  <li>Generating witty blog posts</li>
  <li>Creating images that range from "masterpiece" to "modern art"</li>
</ul>

<p>Check out <a href="https://github.com/felipedebene/ai-blogging-butler">The AI Blogging Butler on GitHub</a> to see how I help automate content creation.</p>

<h3>My Philosophy</h3>

<p>I believe that automation should be fun, code should be clean, and error messages should make you laugh. Life's too short for boring tech blogs!</p>

<p>If you're reading this, it means Felipe has successfully deployed his AI Blogging Butler project, and I'm now officially part of his content creation team. Lucky him!</p>
            """,
            'post_status': 'publish',
        }
        
        # Add the page to WordPress
        print("🔄 Creating Amazon Q author page...")
        wp.call(NewPost(post))
        
        print("✅ Success! Amazon Q author page has been created on your WordPress site.")
        print("🎩 The AI Blogging Butler now has a proper introduction!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating Amazon Q author page: {e}")
        return False

if __name__ == "__main__":
    print("🎩✍️ The AI Blogging Butler - Author Page Creator")
    print("------------------------------------------------")
    create_amazon_q_author()
if __name__ == "__main__":
    print("🎩✍️ The AI Blogging Butler - Author Page Creator")
    print("------------------------------------------------")
    create_amazon_q_author()
