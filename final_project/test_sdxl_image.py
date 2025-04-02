#!/usr/bin/env python
"""
Test script for Stable Diffusion XL image generation
"""

import json
import boto3
import base64
import io
import random
from PIL import Image

# Constants
REGION = "us-west-2"
IMAGE_MODEL_ID = "stability.stable-diffusion-xl-v1"

def main():
    # Initialize Bedrock client
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=REGION
    )
    
    # Test prompt
    prompt = "A cute cat wearing a hat"
    
    try:
        print(f"Generating image with Stable Diffusion XL: '{prompt}'")
        
        # Create request body according to documentation
        request_body = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1.0
                }
            ],
            "cfg_scale": 8.0,
            "steps": 50,
            "seed": random.randint(0, 4294967295),
            "width": 512,
            "height": 512
        }
        
        print(f"Request body: {json.dumps(request_body, indent=2)}")
        
        # Invoke model
        response = bedrock_runtime.invoke_model(
            modelId=IMAGE_MODEL_ID,
            accept='application/json',
            contentType='application/json',
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response.get('body').read())
        print(f"Response keys: {response_body.keys()}")
        
        # Get the base64 encoded image
        base64_image = response_body.get('artifacts')[0].get('base64')
        
        # Convert base64 to image
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))
        
        # Save the image
        image.save("sdxl_test_image.jpg")
        print("Image generated and saved as sdxl_test_image.jpg")
            
    except Exception as e:
        print(f"Error generating image with Stable Diffusion XL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
