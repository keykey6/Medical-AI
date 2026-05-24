from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Header
from pydantic import BaseModel
from typing import Optional, List
from database import save_session, save_chat_log, save_health_profile, get_health_profile, get_health_profile_by_user
from services.health_service import (
    analyze_food_image, analyze_medication_image, generate_tcm_knowledge,
    lookup_medication, search_hospitals, generate_health_assessment,
    get_lifestyle_advice, get_health_knowledge, DISCLAIMER
)
from services.compliance_service import filter_sensitive_words
from services.multimodal_service import validate_image_format, validate_image_size
from services.auth_service import get_current_user
import uuid
import base64

health_router = APIRouter()


def _get_user_or_none(authorization: str | None = Header(None)) -> dict | None:
    return get_current_user(authorization)


class HealthProfileRequest(BaseModel):
    session_id: str
    name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    allergies: Optional[str] = None
    diseases: Optional[str] = None
    medications: Optional[str] = None
    lifestyle: Optional[str] = None


class AssessRequest(BaseModel):
    session_id: str


class QuickQuestionRequest(BaseModel):
    session_id: str
    question: str


class TcmRequest(BaseModel):
    session_id: str
    query: str


class MedicationRequest(BaseModel):
    session_id: str
    query: str


class HospitalRequest(BaseModel):
    session_id: str
    query: str


class LifestyleRequest(BaseModel):
    session_id: str
    category: str = "饮食"


@health_router.get("/profile/{session_id}")
async def get_profile(session_id: str, authorization: str | None = Header(None)):
    user = get_current_user(authorization)

    if user:
        profile = get_health_profile_by_user(user["user_id"])
    else:
        profile = get_health_profile(session_id)

    return {
        "session_id": session_id,
        "profile": profile,
        "is_authenticated": user is not None,
    }


@health_router.post("/profile/save")
async def save_profile(request: HealthProfileRequest, authorization: str | None = Header(None)):
    user = get_current_user(authorization)

    success = save_health_profile(
        session_id=request.session_id,
        user_id=user["user_id"] if user else None,
        name=request.name,
        gender=request.gender,
        age=request.age,
        height=request.height,
        weight=request.weight,
        allergies=request.allergies,
        diseases=request.diseases,
        medications=request.medications,
        lifestyle=request.lifestyle
    )
    if not success:
        raise HTTPException(status_code=500, detail="保存健康档案失败")
    return {"status": "success", "message": "健康档案已保存"}


@health_router.post("/assess")
async def health_assess(request: AssessRequest, authorization: str | None = Header(None)):
    user = get_current_user(authorization)

    if user:
        profile = get_health_profile_by_user(user["user_id"])
    else:
        profile = get_health_profile(request.session_id)

    result = generate_health_assessment(profile)
    save_chat_log(request.session_id, "[健康评估]", result, 'health_assess')
    return {"session_id": request.session_id, "assessment": result}


@health_router.post("/tcm")
async def tcm_consult(request: TcmRequest):
    query = filter_sensitive_words(request.query)
    save_session(request.session_id)
    result = generate_tcm_knowledge(query)
    save_chat_log(request.session_id, f"[中医咨询]{request.query}", result, 'tcm')
    return {"session_id": request.session_id, "response": result}


@health_router.post("/medication")
async def medication_lookup(request: MedicationRequest):
    query = filter_sensitive_words(request.query)
    save_session(request.session_id)
    result = lookup_medication(query)
    save_chat_log(request.session_id, f"[药品查询]{request.query}", result, 'medication')
    return {"session_id": request.session_id, "response": result}


@health_router.post("/medication_image")
async def medication_image_analyze(
    session_id: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    """拍照识别药品包装/说明书/药片"""
    if not file:
        raise HTTPException(status_code=400, detail="请选择要识别的药品图片")

    if not validate_image_format(file.filename):
        raise HTTPException(status_code=400, detail="不支持的图片格式")

    file_content = await file.read()
    if not validate_image_size(len(file_content)):
        raise HTTPException(status_code=400, detail="图片大小超过限制")

    sid = session_id if session_id else str(uuid.uuid4())
    save_session(sid)

    image_base64 = base64.b64encode(file_content).decode('utf-8')
    result = analyze_medication_image(image_base64)

    del image_base64
    del file_content

    save_chat_log(sid, "[药品拍照识别]", result, 'medication_image')
    return {"session_id": sid, "response": result}


@health_router.post("/hospital")
async def hospital_search(request: HospitalRequest):
    query = filter_sensitive_words(request.query)
    save_session(request.session_id)
    result = search_hospitals(query)
    save_chat_log(request.session_id, f"[找医院]{request.query}", result, 'hospital')
    return {"session_id": request.session_id, "response": result}


@health_router.post("/lifestyle")
async def lifestyle_advice(request: LifestyleRequest, authorization: str | None = Header(None)):
    save_session(request.session_id)
    user = get_current_user(authorization)

    profile = None
    if user:
        profile = get_health_profile_by_user(user["user_id"])

    result = get_lifestyle_advice(request.category, profile)
    save_chat_log(request.session_id, f"[生活建议-{request.category}]", result, 'lifestyle')
    return {
        "session_id": request.session_id,
        "response": result,
        "is_personalized": profile is not None,
        "is_authenticated": user is not None,
    }


@health_router.post("/quick_question")
async def quick_question(request: QuickQuestionRequest):
    known_answer = get_health_knowledge(request.question)
    if known_answer:
        save_session(request.session_id)
        save_chat_log(request.session_id, request.question, known_answer, 'quick_qa')
        return {"session_id": request.session_id, "response": known_answer}

    from services.chat_pipeline import ChatPipeline
    pipeline = ChatPipeline(request.session_id)
    result = pipeline.run(request.question)
    save_chat_log(request.session_id, request.question, result.response, 'quick_qa')
    return {"session_id": request.session_id, "response": result.response}


@health_router.post("/food_analyze")
async def food_analyze(
    session_id: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    if not file:
        raise HTTPException(status_code=400, detail="请选择要上传的食物图片")

    if not validate_image_format(file.filename):
        raise HTTPException(status_code=400, detail="不支持的图片格式")

    file_content = await file.read()
    if not validate_image_size(len(file_content)):
        raise HTTPException(status_code=400, detail="图片大小超过限制")

    session_id = session_id if session_id else str(uuid.uuid4())
    save_session(session_id)

    image_base64 = base64.b64encode(file_content).decode('utf-8')

    result = analyze_food_image(image_base64, message)

    del image_base64
    del file_content

    save_chat_log(session_id, f"[食物分析]", result, 'food')

    return {"session_id": session_id, "response": result}
