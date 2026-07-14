from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from retriever import retrieve, embedder
from llm import generate_response
import json

app = FastAPI()

# Memory store
conversation_history = []


@app.on_event("startup")
async def startup_event():
    embedder.encode("warmup query")
    print("Embedder warmed up and ready!")


def update_memory(user, assistant):
    conversation_history.append(f"User: {user}\nAssistant: {assistant}")
    if len(conversation_history) > 5:
        conversation_history.pop(0)


def get_memory():
    return "\n\n".join(conversation_history)


# FIX: root route to prevent 502
@app.post("/")
async def root():
    return {"status": "ok"}


@app.post("/webhook")
async def vapi_webhook(request: Request):
    try:
        body = await request.json()
        print("Incoming:", body)

        message = body.get("message", {})
        msg_type = message.get("type", "")

        # 🔹 Assistant init
        if msg_type == "assistant-request":
            return JSONResponse({
                "assistant": {
                    "firstMessage": "Hey, DevWhisper here. What are you building or debugging?",
                    "model": {
                        "provider": "openai",
                        "model": "gpt-4o",
                        "functions": [{
                            "name": "query_codebase",
                            "description": "Search and explain code or debug errors",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"}
                                },
                                "required": ["query"]
                            }
                        }]
                    },
                    "voice": {"provider": "11labs", "voiceId": "burt"}
                }
            })

        #  Handle BOTH function-call and tool-calls
        if msg_type in ["function-call", "tool-calls"]:

            tools = []

            if msg_type == "function-call":
                tools = [{
                    "id": "single",
                    "function": message.get("functionCall", {})
                }]
            else:
                tools = message.get("toolCalls", [])

            results = []

            for tool in tools:
                fn = tool.get("function", {})
                fn_name = fn.get("name", "")

                # FIX: handle string JSON params
                params = fn.get("arguments") or fn.get("parameters") or {}
                
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse command parameters: {e}")
                        return JSONResponse(
                            status_code=400,
                            content={
  "status": "error",
  "message": "Sorry, I didn't understand that command. Try rephrasing."
})

                if fn_name == "query_codebase":
                    query = params.get("query", "")
                    if not query:
                        return JSONResponse(
                            status_code=400,
                            content={
    "status": "error",
    "message": "Sorry, I didn't understand that command. Try rephrasing."
})

                    context = retrieve(query)
                    print("CONTEXT:", context)
                    history = get_memory()

                    answer = generate_response(query, context, history)

                    update_memory(query, answer)

                    results.append({
                        "toolCallId": tool.get("id", "single"),
                        "result": answer
                    })

            return JSONResponse({"results": results})

        return JSONResponse({"status": "ok"})

    except Exception as e:
        print("SERVER ERROR:", e)
        return JSONResponse(
            status_code=500,
            content={
            "status": "error",
            "message": "An unexpected error occurred."
        })


@app.get("/health")
def health():
    return {"status": "DevWhisper is running"}
