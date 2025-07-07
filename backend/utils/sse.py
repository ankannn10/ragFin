from fastapi.responses import StreamingResponse

def sse_stream(gen):
    """Wrap a generator of str → StreamingResponse with text/event-stream."""
    async def event_generator():
        async for chunk in gen:
            yield f"data: {chunk}\n\n"
    return StreamingResponse(event_generator(),
                             media_type="text/event-stream")
