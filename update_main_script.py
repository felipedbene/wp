#!/usr/bin/env python3
import os
import shutil

# Path to the original script
original_script = '/Users/felipe/workspace/wp/generate_and_publish_post.py'

# Path to the improved image handling script
improved_script = '/Users/felipe/workspace/wp/improved_image_handling.py'

# Backup the original script
backup_path = original_script + '.bak'
shutil.copy2(original_script, backup_path)
print(f"Backed up original script to {backup_path}")

# Read the improved image handling function
with open(improved_script, 'r') as f:
    improved_content = f.read()

# Extract the improved generate_image_with_bedrock function
import re
image_function_match = re.search(r'def generate_image_with_bedrock\(.*?\):(.*?)def', improved_content, re.DOTALL)
if not image_function_match:
    print("Could not find the improved image function in the improved script")
    exit(1)

improved_image_function = "def generate_image_with_bedrock" + image_function_match.group(1)

# Extract the improved process_images_in_content function
process_function_match = re.search(r'def process_images_in_content\(.*?\):(.*?)def', improved_content, re.DOTALL)
if not process_function_match:
    print("Could not find the improved process_images_in_content function in the improved script")
    exit(1)

improved_process_function = "def process_images_in_content" + process_function_match.group(1)

# Read the original script
with open(original_script, 'r') as f:
    original_content = f.read()

# Replace the original image function with the improved one
original_image_function_match = re.search(r'def generate_image_with_bedrock\(.*?\):(.*?)def', original_content, re.DOTALL)
if not original_image_function_match:
    print("Could not find the original image function in the main script")
    exit(1)

updated_content = original_content.replace(
    "def generate_image_with_bedrock" + original_image_function_match.group(1),
    improved_image_function
)

# Add the new process_images_in_content function before the main function
main_function_match = re.search(r'def main\(\):', updated_content)
if not main_function_match:
    print("Could not find the main function in the script")
    exit(1)

insertion_point = main_function_match.start()
updated_content = updated_content[:insertion_point] + improved_process_function + "\n\n" + updated_content[insertion_point:]

# Update the main function to use the new process_images_in_content function
main_function_match = re.search(r'def main\(\):(.*?)if __name__', updated_content, re.DOTALL)
if not main_function_match:
    print("Could not find the main function content")
    exit(1)

main_function_content = main_function_match.group(1)

# Find the image processing section in the main function
image_processing_section_match = re.search(r'# Process content and generate images.*?# Update the post content with images', main_function_content, re.DOTALL)
if not image_processing_section_match:
    print("Could not find the image processing section in the main function")
    exit(1)

# Replace the image processing section with a call to the new function
old_image_processing = image_processing_section_match.group(0)
new_image_processing = """        # Process content and generate images before publishing
        content = post_data['content']
        
        # Process all image placeholders and replace with actual images
        content = process_images_in_content(content)
        
        # Update the post content with images"""

updated_main = main_function_content.replace(old_image_processing, new_image_processing)
updated_content = updated_content.replace(main_function_content, updated_main)

# Write the updated script
with open(original_script, 'w') as f:
    f.write(updated_content)

print(f"Successfully updated {original_script} with improved image handling")
print("You can now run the original script with the improved image handling functionality")
