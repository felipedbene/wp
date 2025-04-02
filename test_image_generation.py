import boto3
import json
import base64
import tempfile

# Constants
AWS_REGION = "us-west-2"  # Explicitly set to us-west-2

def generate_image_with_bedrock(description):
    """Generate an image using Amazon Bedrock's Titan Image Generator"""
    try:
        print(f"Starting image generation for: {description}")
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION
        )
        
        # Prepare the request for Titan Image Generator
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": "A cartoon of a person playing whack-a-mole with computer icons",
                "negativeText": "blurry, distorted, low quality"
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "height": 512,
                "width": 512,
                "cfgScale": 8.0,
                "seed": 42
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
            return None
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    description = "A person playing whack-a-mole with Kubernetes pods"
    image_path = generate_image_with_bedrock(description)
    if image_path:
        print(f"Image generated successfully at: {image_path}")
    else:
        print("Failed to generate image")
