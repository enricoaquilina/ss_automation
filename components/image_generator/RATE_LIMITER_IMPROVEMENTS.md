# Rate Limiter and Error Handling Improvements

## Overview

This document describes the improvements made to the Midjourney integration component to handle Discord API rate limits and provide better error detection and handling for the various Midjourney response scenarios.

## Rate Limiter Implementation

A new `RateLimiter` class has been added to properly manage API requests to Discord, implementing the following features:

1. **Minimum 350ms Delay**: As recommended by Discord's documentation, we now enforce a minimum 350ms delay between all API calls. This approach ensures we remain well under Discord's rate limits, as stated in the UseAPI.net documentation.

2. **Rate Limit Header Tracking**: The system now tracks the rate limit headers (`X-RateLimit-Remaining` and `X-RateLimit-Reset`) returned by Discord and automatically adjusts request timing based on these values.

3. **Exponential Backoff with Jitter**: When retrying failed requests, the system now uses exponential backoff with added jitter to prevent request storms, following best practices for distributed systems.

4. **Endpoint-Specific Limits**: Different Discord API endpoints have different rate limits, and our implementation now tracks these independently.

5. **Configurable Retry Logic**: The system provides control over which status codes should trigger retries, how many retries to attempt, and the base delay between requests.

### Usage Example

```python
# Create a rate limiter with 350ms base delay
rate_limiter = RateLimiter(base_delay=0.35)

# Define the request function
async def send_request():
    await rate_limiter.wait("endpoint_name")
    response = requests.post(url, headers=headers, json=data)
    rate_limiter.update_rate_limits("endpoint_name", response.headers)
    return response

# Send request with retry logic
response = await rate_limiter.with_retry(
    send_request,
    max_retries=3,
    retry_status_codes=[429, 500, 502, 503, 504]
)
```

## Enhanced Error Handling

The system now has specialized error classes and detection logic for all seven Midjourney response scenarios described in the UseAPI.net documentation:

1. **Pre-Moderation Detection**: Detects when a prompt is filtered before being posted to the channel.

2. **Post-Moderation Detection**: Identifies when a generation has started but was stopped by moderation.

3. **Ephemeral Moderation Detection**: Detects when a message was generated but later deleted due to soft moderation.

4. **Job Queuing Detection**: Identifies when a job is queued due to account limitations.

5. **Queue Full Detection**: Recognizes when the Midjourney queue is full.

6. **Invalid Request Handling**: Better error messages for malformed requests or permission issues.

7. **Happy Path Handling**: Improved detection and processing of successful generations.

### Error Hierarchy

The error system uses a class hierarchy to enable targeted exception handling:

```
MidjourneyError (base class)
├── PreModerationError
├── PostModerationError
├── EphemeralModerationError
├── InvalidRequestError
├── QueueFullError
└── JobQueuedError
```

## Generation Flow Improvements

The image generation flow has been upgraded to follow the recommended strategy from UseAPI.net:

1. Get the most recent message ID before sending a command
2. Send the /imagine command using Discord's Interactions API
3. Check the channel every 3-5 seconds for new messages
4. Detect and handle the various response scenarios with appropriate error handling

## Benefits

These improvements provide several key benefits:

1. **Reliability**: The system is much more robust against Discord API rate limits and intermittent failures.

2. **Error Visibility**: Users of the integration can now receive specific, actionable error messages about what went wrong.

3. **Better Resource Management**: The system properly cancels tasks and futures when they're no longer needed.

4. **Compliance**: The implementation now fully follows Discord's recommended API usage patterns and rate limits.

5. **Performance**: By properly handling rate limits, the system can achieve maximum throughput without hitting API limitations.

## Future Enhancements

Possible future enhancements could include:

1. **Request Queuing**: Adding a request queue to batch related API calls for even better rate limit management.

2. **Circuit Breaker Pattern**: Implementing circuit breakers to gracefully handle sustained API issues.

3. **Analytics Integration**: Recording response times and error rates to help tune the system parameters.

4. **Advanced Filtering**: Pre-emptively detecting and rejecting prompts likely to be moderated, saving API calls and credits.