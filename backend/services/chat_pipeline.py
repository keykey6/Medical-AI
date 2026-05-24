import uuid
from dataclasses import dataclass, field
from database import save_session, save_chat_log, get_chat_history, get_session
from services.compliance_service import filter_sensitive_words, is_medical_diagnosis, check_compliance
from services.triage_service import triage_analysis
from services.llm_service import get_llm_response, classify_question, analyze_emotion, generate_comfort
from services.rag_service import search_knowledge_base
from services.knowledge_loader import find_matching_skill, get_skill_workflow


@dataclass
class PipelineResult:
    session_id: str
    response: str
    is_transfer: bool = False
    question_type: str = "其他"
    emotion_type: str = "平静"
    comfort_text: str = ""
    source: str | None = None
    message_type: str = "normal"


@dataclass
class PipelineContext:
    session_id: str
    raw_message: str
    knowledge_context: str = ""
    conversation_history: list = field(default_factory=list)
    extra_prompt: str = ""


class ChatPipeline:
    def __init__(self, session_id: str | None = None, user_id: str | None = None, context: list[dict] | None = None):
        self.user_id = user_id
        self.context = context or []

        if session_id and user_id:
            existing = get_session(session_id)
            if existing and existing.get("user_id") and existing["user_id"] != user_id:
                session_id = None
        self.session_id = session_id or str(uuid.uuid4())

    def _ensure_session(self, message: str = ""):
        existing = get_session(self.session_id)
        title = None
        if self.user_id and (not existing or not existing.get("title")):
            title = message[:40].replace("\n", " ").strip()
        save_session(self.session_id, user_id=self.user_id, title=title)

    def preprocess(self, message: str) -> PipelineResult | None:
        """Compliance/triage check. Returns early-exit result or None to continue.

        先做合规检查（基于原始消息），再做敏感词过滤和分诊分析。
        """
        # 1. Compliance checks on original message (before keyword filtering)
        if is_medical_diagnosis(message):
            response = (
                "抱歉，我无法提供疾病诊断、开处方或治疗方案。"
                "您可以咨询在线医生或前往医院就诊。如需帮助，我可以为您推荐科室或提供就医流程指导。"
            )
            save_chat_log(self.session_id, message, response, "transfer")
            return PipelineResult(
                session_id=self.session_id,
                response=response,
                is_transfer=True,
                message_type="transfer",
            )

        compliance_result = check_compliance(message)
        if not compliance_result["allowed"]:
            save_chat_log(self.session_id, message, compliance_result["message"], "blocked")
            return PipelineResult(
                session_id=self.session_id,
                response=compliance_result["message"],
                is_transfer=True,
                message_type="blocked",
            )

        # 2. Filter sensitive words, then triage
        filtered = filter_sensitive_words(message)
        triage_result = triage_analysis(filtered)
        if triage_result:
            save_chat_log(self.session_id, message, triage_result, "triage")
            return PipelineResult(
                session_id=self.session_id,
                response=triage_result,
                message_type="triage",
            )

        return None

    def build_context(self, message: str) -> tuple[str, list, str, str, str, str | None]:
        """Build knowledge context and classify. Returns (knowledge_context, history, question_type, emotion_type, comfort_text, matched_skill)."""
        matched_skill = find_matching_skill(message)

        question_type = classify_question(message)
        emotion_type = analyze_emotion(message)
        comfort_text = generate_comfort(emotion_type)

        if self.context:
            conversation_history = [
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in self.context[-10:]
            ]
        else:
            conversation_history = get_chat_history(self.session_id, limit=5)

        knowledge_results = search_knowledge_base(message)
        knowledge_context = "\n".join(
            [f"{item['title']}: {item['content'][:300]}" for item in knowledge_results[:3]]
        )

        if matched_skill:
            skill_hint = _build_skill_hint(matched_skill)
            knowledge_context = skill_hint + "\n\n" + knowledge_context

        source = knowledge_results[0]["source_url"] if knowledge_results else None
        return knowledge_context, conversation_history, question_type, emotion_type, comfort_text, source

    def run(self, message: str, image_description: str | None = None) -> PipelineResult:
        self._ensure_session(message)

        early = self.preprocess(message)
        if early:
            return early

        filtered = filter_sensitive_words(message)
        knowledge_context, conversation_history, question_type, emotion_type, comfort_text, source = \
            self.build_context(filtered)

        if image_description:
            llm_prompt = (
                f"图片分析结果：{image_description}\n\n用户问题：{filtered}\n\n"
                "请结合图片分析和用户问题，给出综合性的中文回答。"
            )
        else:
            llm_prompt = filtered

        llm_response = get_llm_response(llm_prompt, knowledge_context, conversation_history)

        final_response = f"{comfort_text}\n\n{llm_response}" if comfort_text else llm_response

        log_message = f"[图片]{filtered}" if image_description and filtered != "[图片]" else message
        message_type = "image" if image_description else "normal"
        save_chat_log(self.session_id, log_message, final_response, message_type)

        return PipelineResult(
            session_id=self.session_id,
            response=final_response,
            question_type=question_type,
            emotion_type=emotion_type,
            comfort_text=comfort_text,
            source=source,
            message_type=message_type,
        )

    def run_image_analysis(self, image_base64: str, user_message: str | None = None) -> PipelineResult:
        from services.multimodal_service import analyze_image

        message = user_message if user_message else "[图片]"
        save_session(self.session_id)

        emotion_type = analyze_emotion(message) if message else "平静"
        comfort_text = generate_comfort(emotion_type)

        description = analyze_image(image_base64, message if message != "[图片]" else "请描述这张图片")

        if message == "[图片]":
            final_response = f"{comfort_text}\n\n{description}" if comfort_text else description
            save_chat_log(self.session_id, "[图片]", final_response, "image")
            return PipelineResult(
                session_id=self.session_id,
                response=final_response,
                question_type="医疗咨询",
                emotion_type=emotion_type,
                message_type="image",
            )

        return self.run(message, description)


def _build_skill_hint(skill_name: str) -> str:
    """根据匹配到的 Skill 构建提示信息，注入到 LLM 上下文中。"""
    workflow = get_skill_workflow(skill_name)

    if skill_name == "ai-pr-medical-report":
        hint = (
            "【系统功能提示】用户的问题匹配到了「AI 医学报告解读」功能。\n"
            "如果用户有检验报告、化验单、体检报告需要解读，请引导用户访问报告解读页面（/static/report.html），"
            "上传报告图片即可获得客观的数据转录和整理。\n"
            "本功能仅进行数据转录，不进行医学诊断。"
        )
        if workflow:
            steps_desc = " → ".join([f"步骤{s['step']}:{s['name']}" for s in workflow])
            hint += f"\n报告解读流程: {steps_desc}"
        return hint

    if skill_name == "baidu-map-api":
        return (
            "【系统功能提示】用户的问题匹配到了「医院地图搜索」功能。\n"
            "请引导用户访问医院地图页面（/static/map.html），可以按城市、科室、等级搜索附近医院，"
            "查看医院地址、电话、科室列表等公开信息。\n"
            "本功能不推荐或评价任何医院，信息仅供参考。\n"
            "如需位置定位，请引导用户在浏览器中授权位置权限。"
        )

    if skill_name == "planning-with-files-zh":
        return (
            "【系统功能提示】用户的问题涉及复杂任务规划。\n"
            "如果需要将任务分解为多步骤执行，可以使用项目规划功能创建 task_plan.md 来跟踪进度。"
        )

    return f"【系统功能提示】用户匹配到了「{skill_name}」功能。请根据该功能的能力范围提供引导。"


