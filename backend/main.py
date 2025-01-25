from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_events.middleware import EventHandlerASGIMiddleware
from fastapi_events.handlers.local import local_handler
from src.routers import model_install
from sse_starlette.sse import EventSourceResponse
from fastapi_events.dispatcher import dispatch
from src.events.events import ModelDownloadStartedEvent
import asyncio
import json

version = 'v1'

app = FastAPI(version=version)

event_handler_id: int = id(app)
app.add_middleware(
    EventHandlerASGIMiddleware,
    handlers=[local_handler],
    middleware_id=event_handler_id,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# event_streams = []

# @app.get("/sse")
# async def sse_endpoint(request: Request):
#     async def event_generator():
#         while True:
#             if await request.is_disconnected():
#                 break
#             if event_streams:
#                 event = event_streams.pop(0)
#                 print(f"event{event}")
#                 yield event
#             await asyncio.sleep(0.1)

#     return EventSourceResponse(event_generator())

# @local_handler.register
# async def handle_event(event):
#     event_name, event_payload = event 
#     print(f"Event received: {event_name}, {event_payload}")
#     formatted_event = {
#         "event": event_name,
#         "data": json.dumps(event_payload) 
#     }
#     event_streams.append(formatted_event) 


# @app.get("/test-event")
# async def test_event():
#     dispatch(
#         ModelDownloadStartedEvent.build(
#             model_id="test-model",
#             download_path="/tmp/test"
#         )
#     )
#     return {"message": "Event dispatched"}

app.include_router(model_install.router, prefix=f"/api/{version}/model_install")






