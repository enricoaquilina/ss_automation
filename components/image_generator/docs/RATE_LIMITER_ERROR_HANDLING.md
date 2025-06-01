# Rate Limiter and Error Handling Implementation

This document describes the implementation of rate limiting and error handling in the Midjourney image generation client.

## Rate Limiting Implementation

The rate limiter implementation follows Discord's API recommendations and includes several key features:

1. **Base Delay Between Requests:**
   - Enforces a minimum 350ms delay between all API calls as recommended by Discord.
   - This approach ensures we stay comfortably under Discord's rate limits with a single thread.
   - The delay doesn't significantly impact overall performance since Midjourney's response time consistently exceeds 350ms.

2. **Rate Limit Header Tracking:**
   - Monitors and respects Discord's rate limit headers (`X-RateLimit-Remaining` and `X-RateLimit-Reset`).
   - Adjusts timing automatically based on per-endpoint rate limits.

3. **Exponential Backoff with Jitter:**
   - Implements exponential backoff with jitter for request retries.
   - Automatically retries failed requests (status codes 429, 500, 502, 503, 504).
   - The backoff algorithm increases wait time exponentially with each retry attempt.
   - Random jitter helps prevent "thundering herd" problems when multiple clients are reconnecting.

4. **Endpoint-Specific Management:**
   - Tracks rate limit information per Discord API endpoint.
   - Enables more granular control over request timing.

## Error Handling Implementation

The client implements specialized error classes for handling the six different Midjourney response scenarios:

1. **PreModerationError:**
   - Occurs when a prompt is pre-moderated and never appears in the channel.
   - Detected when no new message appears in the channel after 30 seconds.

2. **PostModerationError:**
   - Occurs when a prompt appears in the channel but is stopped by moderation.
   - Detected by the presence of a message with content ending in "(Stopped)".
   - Includes the message ID and content in the exception object.

3. **EphemeralModerationError:**
   - Occurs when a message triggers soft moderation and is deleted after completion.
   - Detected when a message we were tracking is no longer found in the channel.

4. **InvalidRequestError:**
   - Occurs when the request format is invalid or has other issues.
   - Typically detected through HTTP 400 status codes or specific error messages.

5. **QueueFullError:**
   - Occurs when the Midjourney queue is currently full.
   - Detected by specific error messages in the response.

6. **JobQueuedError:**
   - Occurs when a job is queued due to account limitations.
   - Includes the message ID in the exception object.

## Client Integration

The MidjourneyClient class properly integrates these features:

1. **Rate Limiter Initialization:**
   - The client initializes the RateLimiter with the recommended 350ms base delay.
   - RateLimiter is used for all API calls in the client.

2. **API Call Wrapping:**
   - API calls are wrapped with the rate limiter's wait method.
   - Headers from responses are used to update rate limit tracking.

3. **Retry Logic:**
   - The with_retry method is used for operations that may fail temporarily.
   - This provides resilience against network issues and temporary Discord API problems.

4. **Error Detection and Handling:**
   - The client detects all six error scenarios through careful message analysis.
   - Appropriate exceptions are raised with detailed information.
   - The error hierarchy allows for both specific and general error catching.

## Testing

We've implemented extensive testing for both the rate limiter and error handling:

1. **Unit Tests:**
   - Tests for all error classes and their hierarchy.
   - Tests for the RateLimiter class functionality including delay enforcement, header tracking, and retry logic.

2. **Integration Tests:**
   - Tests for client's proper initialization and usage of the RateLimiter.
   - Tests for each error detection scenario.

## Conclusion

The implementation of rate limiting and error handling in the Midjourney client follows best practices for Discord API interaction. It ensures reliable and robust operation even in the presence of API limits and various error conditions. The specialized error classes provide detailed information about failure modes, allowing for more intelligent error recovery and user feedback. 