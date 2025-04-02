import boto3
import json
import os
import re
import base64
import random
import tempfile
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, media
from wordpress_xmlrpc.methods.posts import NewPost
from wordpress_xmlrpc.compat import xmlrpc_client
import requests

# Constants
AWS_REGION = "us-west-2"  # Explicitly set to us-west-2
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"  # Using Claude 3 Sonnet model

def get_wp_credentials():
    """Load WordPress credentials from JSON file"""
    try:
        with open('blog-credentials.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def generate_image_with_bedrock(description):
    """Generate an image using Amazon Bedrock's Titan Image Generator with retry logic"""
    for attempt in range(2):  # Try up to 2 times
        try:
            print(f"Starting image generation attempt {attempt + 1} for: '{description}'")
            bedrock_runtime = boto3.client(
                service_name="bedrock-runtime",
                region_name=AWS_REGION
            )
            
            # Clean up the description if it ends with .jpg or other file extensions
            if description.endswith('.jpg') or description.endswith('.png'):
                description = description.rsplit('.', 1)[0]
            
            # Handle hyphenated descriptions by replacing with spaces
            description = description.replace('-', ' ')
            
            # Make the prompt more generic and shorter to avoid validation errors
            # Use a very simple prompt
            if len(description) > 50:
                safe_description = description[:50]
            else:
                safe_description = description
                
            # Make the prompt even safer by removing potentially problematic words
            safe_description = safe_description.replace("banging", "typing on")
            safe_description = safe_description.replace("frustrated", "tired")
            safe_description = safe_description.replace("angry", "unhappy")
                
            # Prepare the request for Titan Image Generator
            request_body = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {
                    "text": f"cartoon {safe_description}",
                    "negativeText": "blurry"
                },
                "imageGenerationConfig": {
                    "numberOfImages": 1,
                    "height": 512,
                    "width": 512,
                    "cfgScale": 8.0,
                    "seed": random.randint(0, 4294967295)
                }
            }
            
            print(f"Calling Bedrock with request: {json.dumps(request_body)}")
            
            # Call Bedrock's Titan Image Generator
            response = bedrock_runtime.invoke_model(
                modelId="amazon.titan-image-generator-v1",
                body=json.dumps(request_body)
            )
            
            # Process the response
            response_body = json.loads(response['body'].read())
            print(f"Got response with keys: {list(response_body.keys())}")
            
            if 'images' in response_body and len(response_body['images']) > 0:
                print(f"Found {len(response_body['images'])} images")
                image_data = base64.b64decode(response_body['images'][0])
                
                # Save to a temporary file
                temp_image = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_image.write(image_data)
                temp_image.close()
                print(f"Image saved to temporary file: {temp_image.name}")
                return temp_image.name
            else:
                print("No images found in response")
                if attempt < 1:  # If this isn't the last attempt
                    continue
                # Generate a funny message image for the last attempt
                return generate_error_message_image("There would be an image here, if I knew how to code!")
        except Exception as e:
            print(f"Error in attempt {attempt + 1} generating image: {str(e)}")
            import traceback
            traceback.print_exc()
            if attempt < 1:  # If this isn't the last attempt
                print("Retrying image generation...")
                continue
            # Generate a funny message image for the last attempt
            return generate_error_message_image("This space intentionally left blank (because the image generation failed)")
    return None  # Should never reach here, but just in case

def generate_error_message_image(message):
    """Generate a simple image with an error message"""
    try:
        # Create a simple image with the error message
        width = 512
        height = 256
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except Exception:
            font = ImageFont.load_default()
        
        # Draw the message
        text_bbox = draw.textbbox((0, 0), message, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        draw.text((x, y), message, font=font, fill='black')
        
        # Save to a temporary file
        temp_image = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        image.save(temp_image.name)
        temp_image.close()
        return temp_image.name
    except Exception as e:
        print(f"Error generating error message image: {str(e)}")
        return None

def process_images_in_content(content):
    """Process all image placeholders in the content and replace them with actual images"""
    # Get WordPress credentials for media upload
    credentials = get_wp_credentials()
    if not credentials:
        print("Failed to get WordPress credentials")
        return content
        
    # Create WordPress client
    wp = Client(
        credentials['xmlrpc_url'],
        credentials['username'],
        credentials['password']
    )
    
    # First, collect all placeholders with different patterns
    image_patterns = [
        r"\[IMAGE: (.*?)\]",
        r"\[Image: (.*?)\]",
        r"\[image: (.*?)\]"
    ]
    
    # Store all placeholders with their positions
    placeholders = []
    
    for pattern in image_patterns:
        for match in re.finditer(pattern, content):
            placeholders.append({
                'full_match': match.group(0),
                'description': match.group(1),
                'start': match.start(),
                'end': match.end()
            })
    
    print(f"Found {len(placeholders)} total image placeholders")
    
    # Sort placeholders by position (to replace from end to beginning)
    # This prevents position shifts when replacing text
    placeholders.sort(key=lambda x: x['start'], reverse=True)
    
    # Process each placeholder
    for placeholder in placeholders:
        description = placeholder['description']
        full_match = placeholder['full_match']
        
        print(f"Processing image placeholder: '{full_match}'")
        
        # Generate image using Bedrock
        image_path = generate_image_with_bedrock(description)
        
        if image_path:
            print(f"Image generated successfully at {image_path}")
            try:
                # Upload image to WordPress
                with open(image_path, 'rb') as img:
                    data = {
                        'name': f'ai-generated-{random.randint(1000, 9999)}.png',
                        'type': 'image/png',
                        'bits': xmlrpc_client.Binary(img.read()),
                        'caption': description
                    }
                
                # Upload to WordPress
                print(f"Uploading image for '{description}' to WordPress...")
                response = wp.call(media.UploadFile(data))
                img_url = response['url']
                print(f"Image uploaded successfully, URL: {img_url}")
                
                # Replace placeholder with actual image HTML
                image_html = f'<figure class="wp-block-image"><img src="{img_url}" alt="{description}"/><figcaption>{description}</figcaption></figure>'
                
                # Replace by slicing the content string at exact positions
                content = content[:placeholder['start']] + image_html + content[placeholder['end']:]
                print(f"Replaced placeholder at position {placeholder['start']}-{placeholder['end']}")
                
                # Clean up temporary file
                os.unlink(image_path)
            except Exception as e:
                print(f"Error uploading image to WordPress: {e}")
                # Replace with a text note since upload failed
                content = content[:placeholder['start']] + f'<p><em>Image description: {description}</em></p>' + content[placeholder['end']:]
        else:
            print(f"Failed to generate image for '{description}', using placeholder text instead")
            # Replace with a text note since image generation failed
            content = content[:placeholder['start']] + f'<p><em>Image description: {description}</em></p>' + content[placeholder['end']:]
    
    return content

def test_image_replacement():
    """Test function to demonstrate image replacement"""
    # Sample content with image placeholders
    test_content = """
    <h2>Test Article</h2>
    <p>This is a test article with some image placeholders.</p>
    
    <p>Here's the first image:</p>
    [IMAGE: A cartoon cat playing with a ball of yarn]
    
    <p>And here's another one:</p>
    [Image: A simple landscape with mountains and trees]
    
    <p>This is the end of the article.</p>
    """
    
    print("Original content:")
    print(test_content)
    print("\n" + "-"*50 + "\n")
    
    # Process the images
    processed_content = process_images_in_content(test_content)
    
    print("Processed content:")
    print(processed_content)

if __name__ == "__main__":
    test_image_replacement()
