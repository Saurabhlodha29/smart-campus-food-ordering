"""
SSE (Server-Sent Events) + Redis pub/sub — stub, implemented in step 12.

Will contain the FastAPI equivalent of SseEmitterRegistry:
  - Redis pub/sub channel naming (preserved from Spring)
  - StreamingResponse / EventSourceResponse for order status pushes
  - Same event payload shape the frontend's OrderTrackingScreen expects
"""
