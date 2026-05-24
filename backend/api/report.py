from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional, List
from database import (
    save_session, save_chat_log, get_chat_history, get_recent_report,
    save_report_record, get_report_records
)
from services.report_service import (
    extract_report_with_llava, generate_report_interpretation,
    generate_structured_data, compute_image_hash,
    get_report_categories, get_report_types, validate_report_interpretation,
    is_report_compliant
)
from services.multimodal_service import validate_image_format, validate_image_size
from services.compliance_service import filter_sensitive_words
from services.llm_service import get_llm_response
from services.rag_service import search_knowledge_base
import uuid
import json
import base64

report_router = APIRouter()


class ReportInterpretRequest(BaseModel):
    session_id: Optional[str] = None
    report_type: str = "其他报告"
    report_description: Optional[str] = None


class ReportInterpretResponse(BaseModel):
    session_id: str
    report_type: str
    report_description: str
    interpretation_result: str
    compliance_check: str
    record_id: Optional[int] = None


class ReportFollowUpRequest(BaseModel):
    session_id: str
    message: str


class ReportFollowUpResponse(BaseModel):
    session_id: str
    response: str


class ReportCategoryItem(BaseModel):
    category: str
    types: List[str]


@report_router.get("/categories")
async def get_categories():
    categories = get_report_categories()
    result = []
    for cat, types in categories.items():
        result.append({"category": cat, "types": types})
    return {"categories": result}


@report_router.get("/types")
async def get_types():
    return {"types": get_report_types()}


@report_router.post("/analyze", response_model=ReportInterpretResponse)
async def analyze_report(
    session_id: Optional[str] = Form(None),
    report_type: str = Form("其他报告"),
    file: UploadFile = File(...)
):
    if not file:
        raise HTTPException(status_code=400, detail="请选择要上传的报告图片")

    if not validate_image_format(file.filename):
        raise HTTPException(status_code=400, detail="不支持的图片格式，请上传JPG、PNG、GIF、BMP或WebP格式的图片")

    file_content = await file.read()

    if not validate_image_size(len(file_content)):
        raise HTTPException(status_code=400, detail="图片大小超过限制，请上传小于15MB的图片")

    session_id = session_id if session_id else str(uuid.uuid4())
    save_session(session_id)

    image_base64 = base64.b64encode(file_content).decode('utf-8')
    image_hash = compute_image_hash(image_base64)

    report_description = extract_report_with_llava(image_base64, report_type)

    if "失败" in report_description or "不可用" in report_description:
        save_chat_log(session_id, f"[报告上传-{report_type}]", report_description, 'report')
        return ReportInterpretResponse(
            session_id=session_id,
            report_type=report_type,
            report_description=report_description,
            interpretation_result=report_description,
            compliance_check="合规",
            record_id=None
        )

    interpretation_result = generate_report_interpretation(report_description, report_type)

    compliant, check_msg = is_report_compliant(interpretation_result)
    if not compliant:
        interpretation_result = validate_report_interpretation(interpretation_result)

    structured = generate_structured_data(report_description, report_type)

    record_id = save_report_record(
        session_id, report_type, report_description,
        structured, interpretation_result, image_hash
    )

    save_chat_log(
        session_id,
        f"[报告解读-{report_type}]",
        interpretation_result,
        'report'
    )

    del image_base64
    del file_content

    return ReportInterpretResponse(
        session_id=session_id,
        report_type=report_type,
        report_description=report_description,
        interpretation_result=interpretation_result,
        compliance_check="合规",
        record_id=record_id
    )


@report_router.post("/analyze_base64", response_model=ReportInterpretResponse)
async def analyze_report_base64(request: ReportInterpretRequest):
    session_id = request.session_id if request.session_id else str(uuid.uuid4())
    save_session(session_id)

    report_type = request.report_type if request.report_type else "其他报告"

    if not request.report_description:
        raise HTTPException(status_code=400, detail="请提供报告描述内容")

    interpretation_result = generate_report_interpretation(request.report_description, report_type)

    compliant, check_msg = is_report_compliant(interpretation_result)
    if not compliant:
        interpretation_result = validate_report_interpretation(interpretation_result)

    structured = generate_structured_data(request.report_description, report_type)

    record_id = save_report_record(
        session_id, report_type, request.report_description,
        structured, interpretation_result
    )

    save_chat_log(
        session_id,
        f"[报告解读-{report_type}]",
        interpretation_result,
        'report'
    )

    return ReportInterpretResponse(
        session_id=session_id,
        report_type=report_type,
        report_description=request.report_description,
        interpretation_result=interpretation_result,
        compliance_check="合规",
        record_id=record_id
    )


@report_router.post("/followup", response_model=ReportFollowUpResponse)
async def report_followup(request: ReportFollowUpRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    message = filter_sensitive_words(request.message)

    recent_report = get_recent_report(request.session_id)

    conversation_history = get_chat_history(request.session_id, limit=5)

    report_context = ""
    if recent_report:
        report_context = f"""
当前会话最近一次报告解读记录：
- 报告类型：{recent_report['report_type']}
- 报告转录内容：{recent_report['report_description'][:500] if recent_report['report_description'] else '无'}
- 解读结果：{recent_report['interpretation_result'][:500] if recent_report['interpretation_result'] else '无'}
"""

    knowledge_results = search_knowledge_base(message)
    knowledge_context = "\n".join([f"{item['title']}: {item['content'][:300]}" for item in knowledge_results[:3]])

    system_context = report_context + "\n\n知识库参考内容：\n" + knowledge_context

    llm_response = get_llm_response(
        message,
        system_context,
        conversation_history
    )

    compliant, check_msg = is_report_compliant(llm_response)
    if not compliant:
        llm_response = validate_report_interpretation(llm_response)

    save_chat_log(request.session_id, message, llm_response, 'report_followup')

    return ReportFollowUpResponse(
        session_id=request.session_id,
        response=llm_response
    )


@report_router.get("/history/{session_id}")
async def get_report_history(session_id: str):
    records = get_report_records(session_id)
    return {
        "session_id": session_id,
        "records": records,
        "total": len(records)
    }


@report_router.get("/recent/{session_id}")
async def get_recent(session_id: str):
    record = get_recent_report(session_id)
    if not record:
        return {"session_id": session_id, "record": None}
    return {"session_id": session_id, "record": record}
