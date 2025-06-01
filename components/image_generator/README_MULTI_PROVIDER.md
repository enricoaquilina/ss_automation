# Multi-Provider Image Generation System

This enhanced system provides reliable image generation for SiliconSentiments Art by supporting multiple AI providers with automatic failover and cost optimization.

## 🎯 Key Features

- **Multiple Providers**: Replicate API (Flux, SDXL, etc.) + existing Midjourney integration
- **Automatic Failover**: If one provider fails, automatically tries the next
- **Cost Optimization**: Choose providers based on cost, speed, or quality preferences  
- **Brand Consistency**: Built-in SiliconSentiments styling and prompt enhancement
- **MongoDB Integration**: Works with your existing Raspberry Pi MongoDB/GridFS setup
- **Instagram Ready**: Optimized for Instagram posting pipeline

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `config.example.json` to `config.json` and update with your credentials:

```json
{
  "providers": {
    "replicate": {
      "api_token": "your_replicate_api_token",
      "default_model": "flux_dev"
    }
  },
  "storage": {
    "mongodb_uri": "mongodb://your_raspberry_pi_ip:27017/",
    "db_name": "silicon_sentiments"
  }
}
```

Or set environment variables:
```bash
export REPLICATE_API_TOKEN="your_token"
export MONGODB_URI="mongodb://your_raspberry_pi:27017/"
```

### 3. Test the Integration

```bash
python test_replicate_integration.py
```

### 4. Generate Images

```bash
# Single image with brand styling
python multi_provider_generate.py "abstract digital art, futuristic cityscape"

# Multiple variations
python multi_provider_generate.py "artistic portrait" --variations 4

# Specific model
python multi_provider_generate.py "landscape art" --model flux_dev

# Cost-optimized generation
python multi_provider_generate.py "concept art" --strategy cost_optimized
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Multi-Provider Service                   │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Replicate   │  │ Midjourney  │  │ Future      │     │
│  │ Provider    │  │ Provider    │  │ Providers   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                            │
                   ┌─────────────────┐
                   │  GridFS Storage │
                   │ (Raspberry Pi)  │
                   └─────────────────┘
                            │
                   ┌─────────────────┐
                   │ Instagram       │
                   │ Publisher       │
                   └─────────────────┘
```

## 🤖 Available Providers

### Replicate Models
- **Flux Dev**: High-quality general purpose (primary)
- **Flux Schnell**: Fast iterations (4x faster, cheaper)
- **SDXL**: Excellent for artistic content
- **Playground v2**: Aesthetic-focused
- **Juggernaut XL**: Photorealistic
- **RealVisXL**: Ultra-realistic

### Provider Selection Strategies
- **Brand Optimized**: Best for SiliconSentiments aesthetic
- **Cost Optimized**: Cheapest providers first
- **Speed Optimized**: Fastest generation
- **Quality Optimized**: Highest quality models

## 📊 Cost Comparison

| Provider | Model | Cost/Image | Speed | Quality |
|----------|-------|------------|-------|---------|
| Replicate | Flux Schnell | $0.003 | ~10s | Good |
| Replicate | SDXL | $0.0095 | ~30s | Excellent |
| Replicate | Flux Dev | $0.055 | ~60s | Excellent |
| Midjourney | Standard | ~$0.02 | ~90s | Excellent |

## 🎨 SiliconSentiments Brand Integration

The system automatically enhances prompts for brand consistency:

```python
# Original prompt
"abstract digital landscape"

# Enhanced for SiliconSentiments
"abstract digital landscape, digital art, modern, clean aesthetic, 
tech-inspired, vibrant colors, high contrast, visually striking"
```

## 🔧 Integration with Existing System

### With Instagram Publisher

```python
from multi_provider_service import MultiProviderGenerationService

# Generate images
service = MultiProviderGenerationService(config)
response = await service.generate_image(request)

# Images are automatically saved to MongoDB/GridFS
# Your existing Instagram publisher can use the storage_ids
for storage_id in response.storage_ids:
    # Use with existing InstagramCarouselPublisher
    pass
```

### Failover Example

```python
# If Midjourney is down, automatically uses Replicate
response = await service.generate_image(GenerationRequest(
    prompt="digital art",
    strategy=ProviderStrategy.BRAND_OPTIMIZED  # Tries: Flux Dev → SDXL → Midjourney
))
```

## 📈 Monitoring & Analytics

The service tracks usage statistics:

```python
stats = service.get_stats()
print(f"Total generations: {stats['total_generations']}")
print(f"Success rate: {stats['successful_generations'] / stats['total_generations']}")
print(f"Total cost: ${stats['total_cost']:.2f}")
print(f"Provider usage: {stats['provider_usage']}")
```

## 🚨 Error Handling

The system handles various error scenarios:

- **Authentication errors**: Invalid API tokens
- **Quota errors**: Rate limits or account limits
- **Moderation errors**: Content policy violations
- **Timeout errors**: Generation taking too long
- **Network errors**: Connectivity issues

Each error type is handled appropriately with automatic fallback to other providers when possible.

## 🔄 Migration from Midjourney-only

1. **Install new dependencies**: `pip install replicate`
2. **Add Replicate config**: Set up API token
3. **Test integration**: Run test script
4. **Update generation scripts**: Use `multi_provider_generate.py`
5. **Monitor performance**: Check stats and costs

## 🎯 Benefits for SiliconSentiments Art

1. **Reliability**: If Midjourney has issues, Replicate provides backup
2. **Cost Control**: Choose cheaper models for iterations, premium for final posts
3. **Speed**: Use fast models for testing prompts, slower for final generation
4. **Consistency**: Brand-specific prompt enhancement
5. **Scalability**: Generate multiple variations efficiently
6. **Analytics**: Track what works best for your audience

## 🔮 Future Enhancements

- **Content Analysis**: AI-powered prompt optimization based on successful posts
- **Trend Detection**: Generate content based on Instagram trends
- **Style Transfer**: Apply successful post styles to new content
- **3D Integration**: Convert 2D art to 3D printable models
- **Video Generation**: Animate static art for Instagram Reels

## 📞 Support

For issues or questions:
1. Check logs for error details
2. Verify API tokens and connectivity
3. Test with simple prompts first
4. Review provider status pages
5. Check MongoDB connection

---

*This system is designed to get SiliconSentiments Art back to consistent daily posting while building toward a comprehensive content creation platform.*