# Changelog

## [1.2.0] - 2025-04-02

### Fixed
- Switched from Amazon Titan Image Generator to Stable Diffusion XL for more reliable image generation
- Fixed image generation request format to properly work with Stable Diffusion XL
- Updated response parsing to extract images from the correct field in the response

### Added
- Test script for Stable Diffusion XL image generation

## [1.1.0] - 2025-04-02

### Added
- Amazon Q author page creation script
- Amazon Q showcase post generator
- Author introduction page on WordPress

## [1.0.0] - 2025-04-02

### Added
- Initial release of The AI Blogging Butler
- WordPress post generation using Claude 3 Sonnet
- Image generation using Stable Diffusion XL
- Multi-architecture Docker images (ARM64/AMD64)
- Kubernetes deployment with CronJob scheduling
- Comprehensive documentation and setup scripts

### Fixed
- Docker Hub repository path corrected to fdebene/ai-butler
- JSON parsing issues with Claude's responses
- Image placeholder handling for various formats

## [0.1.0] - 2025-03-15

### Added
- Initial prototype with basic WordPress integration
- Claude 3 Sonnet integration for content generation
- Simple image generation capabilities
