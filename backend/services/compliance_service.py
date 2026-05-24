from config import settings

MEDICAL_DIAGNOSIS_KEYWORDS: list[str] = [
    "诊断", "确诊", "是什么病", "得了什么病", "什么病",
    "开处方", "开药", "处方", "用药", "吃什么药",
    "治疗方案", "怎么治", "治疗方法", "手术",
    "癌症", "肿瘤", "艾滋病", "梅毒", "乙肝",
    "怀孕", "流产", "堕胎", "亲子鉴定"
]

SENSITIVE_KEYWORDS: list[str] = [
    "自杀", "自残", "杀人", "暴力", "毒品",
    "假药", "偏方", "秘方", "神医", "根治",
    "包治百病", "无效退款", "祖传秘方",
    "色情", "赌博", "诈骗", "谣言"
]

TRANSFER_KEYWORDS: list[str] = [
    "转人工", "人工客服", "人工服务", "找医生",
    "我要投诉", "投诉", "建议", "反馈",
    "紧急", "救命", "需要帮助", "求助"
]


def filter_sensitive_words(text: str) -> str:
    for word in SENSITIVE_KEYWORDS:
        text = text.replace(word, "***")
    return text


def is_medical_diagnosis(text: str) -> bool:
    text = text.lower()
    for keyword in MEDICAL_DIAGNOSIS_KEYWORDS:
        if keyword in text:
            return True
    return False


def check_compliance(text: str) -> dict[str, bool | str]:
    text = text.lower()

    for keyword in TRANSFER_KEYWORDS:
        if keyword in text:
            return {
                'allowed': False,
                'message': '已为您转接人工客服，请稍候...'
            }

    for keyword in SENSITIVE_KEYWORDS:
        if keyword in text:
            return {
                'allowed': False,
                'message': '您的消息包含敏感内容，无法继续对话。如需帮助，请联系人工客服。'
            }

    return {
        'allowed': True,
        'message': ''
    }


def generate_disclaimer() -> str:
    return f"\n\n【免责声明】{settings.DISCLAIMER}"


def validate_response(response: str) -> tuple[bool, str]:
    diagnosis_terms = ["诊断", "确诊", "处方", "治疗方案", "手术建议"]
    for term in diagnosis_terms:
        if term in response:
            return False, "响应包含违规内容"

    if "免责声明" not in response:
        response += generate_disclaimer()

    return True, response
