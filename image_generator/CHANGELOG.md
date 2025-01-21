# Changelog

All notable changes to the image generator will be documented in this file.

## [Unreleased]

### Added
- Support for Midjourney v6.0 model variation
  - Added v6.0 handling in GenerationService._process_variation()
  - Added v6.0 handling in MidjourneyClient.generate()
  - Added comprehensive documentation for version handling in both files

### Changed
- Improved documentation around version handling and variation support
  - Added supported variations list to GenerationService
  - Added supported options documentation to MidjourneyClient
  - Added warning notes about adding new versions/variations

### Technical Details
Files modified:
1. `image_generator/generation_service.py`:
   - Added v6.0 case in options dictionary construction
   - Added documentation about supported variations
   - Added warning about adding new variations

2. `image_generator/providers/midjourney/client.py`:
   - Added v6.0 case in options string construction
   - Added detailed options documentation
   - Added warning about adding new versions

The changes ensure proper handling of the --v 6.0 parameter in both the service layer and the client implementation. 