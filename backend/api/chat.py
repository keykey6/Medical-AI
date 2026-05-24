import json
import base64

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile, Header
from pydantic import BaseModel

from database import save_chat_log, get_chat_history
from services.chat_pipeline import ChatPipeline, PipelineResult
from services.llm_service import get_llm_response_stream
from services.auth_service import get_current_user
from services.multimodal_service import validate_image_format, validate_image_size
from services.speech_service import speech_to_text, is_whisper_available

chat_router = APIRouter()


# ── Request / Response models ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    context: list[dict] | None = None  # [{role, content}, ...] 对话上下文


class ChatResponse(BaseModel):
    session_id: str
    response: str
    is_transfer: bool = False
    source: str | None = None
    question_type: str | None = None
    emotion_type: str | None = None


class ChatWithTypeResponse(BaseModel):
    session_id: str
    response: str
    is_transfer: bool = False
    question_type: str
    emotion_type: str
    comfort_text: str


class HistoryItem(BaseModel):
    user_message: str
    ai_response: str
    created_at: str


class HistoryResponse(BaseModel):
    session_id: str
    history: list[HistoryItem]


class ImageChatRequest(BaseModel):
    session_id: str | None = None
    message: str | None = None
    image_base64: str


def _pipeline_to_response(result: PipelineResult) -> ChatResponse:
    return ChatResponse(
        session_id=result.session_id,
        response=result.response,
        is_transfer=result.is_transfer,
        source=result.source,
        question_type=result.question_type,
        emotion_type=result.emotion_type,
    )


def _pipeline_to_typed_response(result: PipelineResult) -> ChatWithTypeResponse:
    return ChatWithTypeResponse(
        session_id=result.session_id,
        response=result.response,
        is_transfer=result.is_transfer,
        question_type=result.question_type,
        emotion_type=result.emotion_type,
        comfort_text=result.comfort_text,
    )


# ── Core endpoints ─────────────────────────────────────────────────────────

@chat_router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest, authorization: str | None = Header(None)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    user = get_current_user(authorization)
    pipeline = ChatPipeline(request.session_id, user_id=user["user_id"] if user else None)
    result = pipeline.run(request.message)
    return _pipeline_to_response(result)


@chat_router.post("/send_with_type", response_model=ChatWithTypeResponse)
async def send_message_with_type(request: ChatRequest, authorization: str | None = Header(None)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    user = get_current_user(authorization)
    pipeline = ChatPipeline(
        request.session_id, 
        user_id=user["user_id"] if user else None,
        context=request.context  # 传入上下文
    )
    result = pipeline.run(request.message)
    return _pipeline_to_typed_response(result)


@chat_router.post("/send_image")
async def send_image_message(
    session_id: str | None = None,
    message: str | None = None,
    file: UploadFile = File(...),
):
    if not file:
        raise HTTPException(status_code=400, detail="请选择要上传的图片")
    if not validate_image_format(file.filename):
        raise HTTPException(status_code=400, detail="不支持的图片格式，请上传JPG、PNG、GIF、BMP或WebP格式的图片")

    file_content = await file.read()
    if not validate_image_size(len(file_content)):
        raise HTTPException(status_code=400, detail="图片大小超过限制，请上传小于10MB的图片")

    image_base64 = base64.b64encode(file_content).decode("utf-8")
    pipeline = ChatPipeline(session_id)
    result = pipeline.run_image_analysis(image_base64, message)

    return {
        "session_id": result.session_id,
        "response": result.response,
        "is_transfer": False,
        "question_type": result.question_type,
        "emotion_type": result.emotion_type,
    }


@chat_router.post("/send_image_base64")
async def send_image_base64(request: ImageChatRequest):
    if not request.image_base64:
        raise HTTPException(status_code=400, detail="请提供图片数据")

    pipeline = ChatPipeline(request.session_id)
    result = pipeline.run_image_analysis(request.image_base64, request.message)

    return {
        "session_id": result.session_id,
        "response": result.response,
        "is_transfer": False,
        "question_type": result.question_type,
        "emotion_type": result.emotion_type,
    }


# ── WebSocket ──────────────────────────────────────────────────────────────

@chat_router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    pipeline = ChatPipeline(session_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message = message_data["message"]

            pipeline._ensure_session(message)

            early = pipeline.preprocess(message)
            if early:
                await websocket.send_json({
                    "response": early.response, "is_transfer": early.is_transfer, "done": True
                })
                continue

            knowledge_context, conversation_history, question_type, emotion_type, comfort_text, _ = \
                pipeline.build_context(message)

            full_response = ""
            if comfort_text:
                full_response = comfort_text + "\n\n"
                await websocket.send_json({
                    "response": full_response, "is_transfer": False, "done": False
                })

            async for chunk in get_llm_response_stream(message, knowledge_context, conversation_history):
                full_response += chunk
                await websocket.send_json({
                    "response": full_response, "is_transfer": False, "done": False
                })

            await websocket.send_json({
                "response": full_response, "is_transfer": False, "done": True,
                "question_type": question_type, "emotion_type": emotion_type,
            })

            save_chat_log(session_id, message, full_response, "normal")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()


# ── History / Transfer / Speech ────────────────────────────────────────────

@chat_router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    history = get_chat_history(session_id)
    # 确保datetime对象转换为字符串
    safe_history = []
    for item in (history or []):
        safe_item = dict(item)
        if hasattr(safe_item.get('created_at'), 'isoformat'):
            safe_item['created_at'] = safe_item['created_at'].isoformat()
        elif isinstance(safe_item.get('created_at'), str):
            pass  # 已经是字符串
        else:
            safe_item['created_at'] = str(safe_item.get('created_at', ''))
        safe_history.append(safe_item)
    return HistoryResponse(session_id=session_id, history=safe_history)


@chat_router.post("/transfer/{session_id}")
async def transfer_to_human(session_id: str):
    response = "已为您转接人工客服，请稍候..."
    save_chat_log(session_id, "[请求转人工]", response, "transfer")
    return {"status": "success", "message": response}


@chat_router.post("/speech_to_text")
async def speech_to_text_endpoint(audio: UploadFile = File(...)):
    if not audio:
        raise HTTPException(status_code=400, detail="请上传音频文件")

    if not is_whisper_available():
        return {"text": "语音识别服务未就绪，请先安装Whisper"}

    audio_content = await audio.read()
    text = speech_to_text(audio_content, "wav")
    return {"text": text}
