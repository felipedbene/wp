import boto3
import json
import base64
import tempfile
import random

# Constants
AWS_REGION = "us-west-2"  # Explicitly set to us-west-2

def generate_image_with_bedrock(description):
    """Generate an image using Amazon Bedrock's Stable Diffusion model instead of Titan"""
    try:
        print(f"Starting image generation for: {description}")
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION
        )
        
        # Clean up the description to make it safer
        safe_description = description
        if len(safe_description) > 50:
            safe_description = safe_description[:50]
        
        # Replace potentially problematic words
        safe_description = safe_description.replace("banging", "typing on")
        safe_description = safe_description.replace("frustrated", "tired")
        safe_description = safe_description.replace("angry", "unhappy")
        
        # Use Stable Diffusion instead of Titan
        # Prepare the request for Stable Diffusion
        request_body = {
            "text_prompts": [
                {
                    "text": f"A simple cartoon illustration of {safe_description}, digital art style, clean lines",
                    "weight": 1.0
                },
                {
                    "text": "blurry, distorted, low quality, nsfw, violent",
                    "weight": -1.0
                }
            ],
            "cfg_scale": 7.0,
            "seed": random.randint(0, 4294967295),
            "steps": 30,
            "width": 512,
            "height": 512
        }
        
        print(f"Calling Bedrock with request: {json.dumps(request_body)}")
        
        # Call Bedrock's Stable Diffusion model
        response = bedrock_runtime.invoke_model(
            modelId="stability.stable-diffusion-xl-v1",
            body=json.dumps(request_body)
        )
        
        # Process the response
        response_body = json.loads(response['body'].read())
        
        if 'artifacts' in response_body and len(response_body['artifacts']) > 0:
            print(f"Found {len(response_body['artifacts'])} images")
            image_data = base64.b64decode(response_body['artifacts'][0]['base64'])
            
            # Save to a temporary file
            temp_image = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_image.write(image_data)
            temp_image.close()
            print(f"Image saved to temporary file: {temp_image.name}")
            return temp_image.name
        else:
            print("No images found in response")
            return None
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    description = "A person working on a computer with colorful code on screen"
    image_path = generate_image_with_bedrock(description)
    if image_path:
        print(f"Image generated successfully at: {image_path}")
    else:
        print("Failed to generate image")
