import json
import logging

import requests

from config import settings

logger = logging.getLogger("app.llm")

CURRENT_MODEL = settings.CURRENT_MODEL


def set_model(model_type: str) -> None:
    global CURRENT_MODEL
    CURRENT_MODEL = model_type


def get_llm_response(prompt: str, context: str = "", conversation_history=None) -> str:
    if CURRENT_MODEL == "deepseek":
        return _get_deepseek_response(prompt, context, conversation_history)
    return _get_ollama_response(prompt, context, conversation_history)


async def get_llm_response_stream(prompt: str, context: str = "", conversation_history=None):
    if CURRENT_MODEL == "deepseek":
        async for chunk in _get_deepseek_stream(prompt, context, conversation_history):
            yield chunk
    else:
        async for chunk in _get_ollama_stream(prompt, context, conversation_history):
            yield chunk


def classify_question(prompt: str) -> str:
    system_prompt = (
        "你是一个专业的医疗问题分类器。请将用户的问题分类为以下类别之一：\n"
        "- 医疗咨询：关于疾病症状、健康知识、用药常识等医疗相关问题\n"
        "- 预约挂号：关于医院挂号流程、预约方式、科室选择等问题\n"
        "- 费用查询：关于医疗费用、医保报销、收费标准等问题\n"
        "- 医保政策：关于医保政策、报销比例、异地就医等问题\n"
        "- 科室介绍：关于医院科室设置、科室职能、专家介绍等问题\n"
        "- 其他：不属于以上类别的问题\n\n"
        "请只输出分类结果，不需要额外解释。"
    )
    if CURRENT_MODEL == "deepseek":
        result = _deepseek_generate(prompt, system_prompt, max_tokens=50, temperature=0.1)
        if result:
            return result
    return _ollama_generate(prompt, system_prompt, max_tokens=50, temperature=0.1) or "其他"


def analyze_emotion(prompt: str) -> str:
    system_prompt = (
        "你是一个情绪分析助手。请分析用户问题中的情绪，判断其情绪类型：\n"
        "- 平静：用户语气平和，没有明显情绪\n"
        "- 焦虑：用户表达担忧、紧张、不安等情绪\n"
        "- 愤怒：用户表达不满、生气、抱怨等情绪\n"
        "- 急迫：用户表达急切、紧急等情绪\n"
        "- 困惑：用户表达疑惑、不确定等情绪\n\n"
        "请只输出情绪类型，不需要额外解释。"
    )
    if CURRENT_MODEL == "deepseek":
        result = _deepseek_generate(prompt, system_prompt, max_tokens=50, temperature=0.1)
        if result:
            return result
    return _ollama_generate(prompt, system_prompt, max_tokens=50, temperature=0.1) or "平静"


def generate_comfort(emotion_type: str) -> str:
    comfort_map = {
        "焦虑": "我理解您的担忧，请不要过于担心，保持良好心态对健康很重要。",
        "愤怒": "非常抱歉给您带来不便，我们会尽力为您解决问题。",
        "急迫": "请您先不要着急，我会尽快为您提供帮助。",
        "困惑": "我明白您的疑惑，让我为您详细解释一下。",
        "平静": "",
    }
    return comfort_map.get(emotion_type, "")


# ── Ollama ──────────────────────────────────────────────────────────────────

def _build_system_prompt(context: str, conversation_history) -> str:
    history_text = ""
    if conversation_history:
        for item in conversation_history[-5:]:
            history_text += f"用户: {item.get('user_message', '')}\n助手: {item.get('ai_response', '')}\n"

    skills_context = ""
    try:
        from services.knowledge_loader import get_available_skills_context
        skills_context = get_available_skills_context()
    except Exception:
        pass

    return (
        "你是一个专业的医疗健康知识问答助手。请严格遵守以下规则：\n\n"
        "1. **合规要求**：\n"
        "   - 不得进行疾病诊断\n"
        "   - 不得开具处方\n"
        "   - 不得提供治疗方案\n"
        "   - 所有回答必须包含免责声明\n\n"
        "2. **知识来源**：\n"
        "   - 优先使用提供的知识库内容\n"
        "   - 引用权威医疗信息来源\n\n"
        "3. **回答风格**：\n"
        "   - 使用通俗易懂的语言\n"
        "   - 结构清晰，逻辑严谨\n"
        "   - 保持专业但亲切的语气\n\n"
        f"4. **对话历史**：\n{history_text}\n\n"
        f"5. **知识库内容**：\n{context}\n\n"
        "6. **免责声明**：\n"
        "   - 必须在回答末尾添加：\"本文仅供科普参考，不构成医疗建议。如有不适，请及时就医。\"\n\n"
        f"{skills_context}"
    )


def _ollama_generate(prompt: str, system: str, max_tokens: int = 50, temperature: float = 0.1) -> str | None:
    try:
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        data = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature, "max_tokens": max_tokens},
        }
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception:
        logger.warning("Ollama分类/情绪分析失败", exc_info=True)
    return None


def _deepseek_generate(prompt: str, system: str, max_tokens: int = 50, temperature: float = 0.1) -> str | None:
    try:
        if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY == "your_deepseek_api_key_here":
            return None
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(settings.DEEPSEEK_API_URL, json=data, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        logger.warning("DeepSeek分类/情绪分析失败", exc_info=True)
    return None


def _get_ollama_response(prompt: str, context: str = "", conversation_history=None) -> str:
    try:
        system_prompt = _build_system_prompt(context, conversation_history)
        data = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": 0.3, "max_tokens": 2000},
        }
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate", json=data, timeout=60
        )
        if response.status_code == 200:
            return response.json().get("response", "")
        logger.error(f"Ollama请求失败: {response.status_code}")
        return _get_deepseek_response(prompt, context, conversation_history)
    except Exception:
        logger.warning("Ollama调用失败，切换到DeepSeek", exc_info=True)
        return _get_deepseek_response(prompt, context, conversation_history)


async def _get_ollama_stream(prompt: str, context: str = "", conversation_history=None):
    try:
        system_prompt = _build_system_prompt(context, conversation_history)
        data = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": True,
            "options": {"temperature": 0.3, "max_tokens": 2000},
        }
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate", json=data, stream=True, timeout=60
        )
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    try:
                        result = json.loads(line)
                        if "response" in result:
                            yield result["response"]
                        if result.get("done"):
                            break
                    except json.JSONDecodeError:
                        pass
        else:
            async for chunk in _get_deepseek_stream(prompt, context, conversation_history):
                yield chunk
    except Exception:
        logger.warning("Ollama流式调用失败，切换到DeepSeek", exc_info=True)
        async for chunk in _get_deepseek_stream(prompt, context, conversation_history):
            yield chunk


# ── DeepSeek ────────────────────────────────────────────────────────────────

def _get_deepseek_response(prompt: str, context: str = "", conversation_history=None) -> str:
    try:
        if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY == "your_deepseek_api_key_here":
            return (
                "请在.env文件中配置DeepSeek API密钥以使用外部模型。\n\n"
                "本文仅供科普参考，不构成医疗建议。如有不适，请及时就医。"
            )

        system_prompt = _build_system_prompt(context, conversation_history)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2000,
        }
        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(settings.DEEPSEEK_API_URL, json=data, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        logger.error(f"DeepSeek请求失败: {response.status_code}")
        return _get_ollama_response(prompt, context, conversation_history)
    except Exception:
        logger.warning("DeepSeek调用失败，切换到Ollama", exc_info=True)
        return _get_ollama_response(prompt, context, conversation_history)


async def _get_deepseek_stream(prompt: str, context: str = "", conversation_history=None):
    try:
        if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY == "your_deepseek_api_key_here":
            yield "请在.env文件中配置DeepSeek API密钥以使用外部模型。"
            return

        system_prompt = _build_system_prompt(context, conversation_history)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2000,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(settings.DEEPSEEK_API_URL, json=data, headers=headers, stream=True, timeout=60)
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                        if line == "[DONE]":
                            break
                        try:
                            result = json.loads(line)
                            if result.get("choices"):
                                delta = result["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            pass
        else:
            async for chunk in _get_ollama_stream(prompt, context, conversation_history):
                yield chunk
    except Exception:
        logger.warning("DeepSeek流式调用失败，切换到Ollama", exc_info=True)
        async for chunk in _get_ollama_stream(prompt, context, conversation_history):
            yield chunk
