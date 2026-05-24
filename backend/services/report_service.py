import os
import re
import json
import base64
import requests
import hashlib
import tempfile

from config import settings

MEDICAL_DIAGNOSIS_BLOCKLIST = [
    "诊断", "确诊", "患病", "得病", "病症是", "可能是", "怀疑是",
    "治疗方案", "治疗建议", "用药建议", "服用", "口服", "注射",
    "处方", "开药", "剂量", "用法用量", "每日一次", "每日两次",
    "手术", "切除", "化疗", "放疗", "靶向治疗",
    "预后", "存活率", "治愈率", "晚期", "早期",
    "需要治疗", "必须", "应该去", "赶紧去",
    "建议用药", "药物", "药品", "抗生素", "消炎药",
]

REPORT_TYPE_PROMPTS = {
    "血常规": "请识别并客观转述这份血常规化验单上的所有项目名称和数值，包括白细胞计数、红细胞计数、血红蛋白、血小板计数、中性粒细胞百分比、淋巴细胞百分比等指标及其参考范围。仅转述数据，不进行分析或诊断。",
    "尿常规": "请识别并客观转述这份尿常规化验单上的所有项目名称和数值，包括尿蛋白、尿糖、尿潜血、尿白细胞、尿比重、酸碱度等指标及其参考范围。仅转述数据，不进行分析或诊断。",
    "肝功能": "请识别并客观转述这份肝功能化验单上的所有项目名称和数值，包括谷丙转氨酶、谷草转氨酶、总胆红素、直接胆红素、总蛋白、白蛋白等指标及其参考范围。仅转述数据，不进行分析或诊断。",
    "肾功能": "请识别并客观转述这份肾功能化验单上的所有项目名称和数值，包括肌酐、尿素氮、尿酸、胱抑素C等指标及其参考范围。仅转述数据，不进行分析或诊断。",
    "血脂": "请识别并客观转述这份血脂化验单上的所有项目名称和数值，包括总胆固醇、甘油三酯、高密度脂蛋白胆固醇、低密度脂蛋白胆固醇等指标及其参考范围。仅转述数据，不进行分析或诊断。",
    "血糖": "请识别并客观转述这份血糖化验单上的所有项目名称和数值，包括空腹血糖、餐后血糖、糖化血红蛋白等指标及其参考范围。仅转述数据，不进行分析或诊断。",
    "心电图": "请识别并客观描述这份心电图报告的内容，包括心率、心律类型、PR间期、QRS时限、QT间期等检查所见以及报告结论部分。仅转录原始报告内容，不进行任何医学解释或诊断。",
    "超声检查": "请识别并客观描述这份超声检查报告的内容，包括检查部位、超声所见描述、检查结论等。仅转录原始报告内容，不进行任何医学解释或诊断。",
    "X光检查": "请识别并客观描述这份X光检查报告的内容，包括检查部位、影像所见描述、检查结论等。仅转录原始报告内容，不进行任何医学解释或诊断。",
    "CT检查": "请识别并客观描述这份CT检查报告的内容，包括检查部位、扫描所见描述、检查结论等。仅转录原始报告内容，不进行任何医学解释或诊断。",
    "磁共振检查": "请识别并客观描述这份磁共振检查报告的内容，包括检查部位、扫描所见描述、检查结论等。仅转录原始报告内容，不进行任何医学解释或诊断。",
    "甲状腺功能": "请识别并客观转述这份甲状腺功能化验单上的所有项目名称和数值，包括促甲状腺激素、游离T3、游离T4、甲状腺过氧化物酶抗体等指标及其参考范围。仅转述数据，不进行分析或诊断。",
    "肿瘤标志物": "请识别并客观转述这份肿瘤标志物化验单上的所有项目名称和数值，包括甲胎蛋白、癌胚抗原、CA125、CA199等指标及其参考范围。仅转述数据，不进行分析或诊断。",
    "电解质": "请识别并客观转述这份电解质化验单上的所有项目名称和数值，包括钾、钠、氯、钙、镁等指标及其参考范围。仅转述数据，不进行分析或诊断。",
    "凝血功能": "请识别并客观转述这份凝血功能化验单上的所有项目名称和数值，包括凝血酶原时间、活化部分凝血活酶时间、纤维蛋白原等指标及其参考范围。仅转述数据，不进行分析或诊断。",
    "其他报告": "请识别并客观描述这份医疗报告的内容，包括各项检查项目、数值、参考范围以及报告结论。仅转录原始报告内容，不进行任何医学解释或诊断。",
}

REPORT_CATEGORIES = {
    "血液检查": ["血常规", "血脂", "血糖", "凝血功能", "电解质"],
    "生化检查": ["肝功能", "肾功能", "甲状腺功能", "肿瘤标志物"],
    "影像检查": ["心电图", "超声检查", "X光检查", "CT检查", "磁共振检查"],
    "其他": ["其他报告"],
}

def get_report_categories():
    return REPORT_CATEGORIES

def get_report_types():
    return list(REPORT_TYPE_PROMPTS.keys())

def extract_report_with_llava(image_base64, report_type="其他报告"):
    try:
        url = "http://localhost:11434/api/generate"

        analysis_prompt = REPORT_TYPE_PROMPTS.get(report_type, REPORT_TYPE_PROMPTS["其他报告"])

        system_prompt = """
你是一个专业的医疗报告转录助手。请严格遵守以下规则：

1. 核心规则（必须遵守）：
   - 仅对报告上的文字内容进行客观转录
   - 严禁进行任何医学诊断、病情分析或健康评估
   - 严禁对任何指标是否正常做出判断
   - 严禁使用"异常"、"偏高"、"偏低"、"正常"、"有问题"等评判性词汇
   - 严禁提出任何就医建议、用药建议或治疗方案
   - 仅可以使用"检测项目名称+检测数值+参考范围"的格式进行转录

2. 语言要求：
   - 所有输出必须使用纯中文
   - 如果报告中有英文缩写（如WBC、RBC等），需要同时给出中文全称

3. 输出格式：
   - 使用结构化格式列出各项指标
   - 格式示例：
     项目名称：白细胞计数（WBC）
     检测结果：6.5
     参考范围：3.5-9.5（单位：×10⁹/L）
"""

        data = {
            "model": settings.OLLAMA_MULTIMODAL_MODEL,
            "prompt": analysis_prompt,
            "system": system_prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "max_tokens": 2000
            }
        }

        response = requests.post(url, json=data, timeout=120)

        if response.status_code == 200:
            result = response.json()
            raw_description = result.get("response", "").strip()
            cleaned = filter_report_response(raw_description)
            return cleaned
        else:
            return "报告图像识别失败，请确认上传的图片清晰可读后重试。"

    except Exception as e:
        print(f"报告提取异常: {e}")
        return "报告识别服务暂时不可用，请稍后重试。"

def filter_report_response(text):
    text = re.sub(r'[a-zA-Z]{3,}', lambda m: '', text)
    if len(text.strip()) < 10:
        return text
    return text

def generate_report_interpretation(report_description, report_type):
    try:
        url = "http://localhost:11434/api/generate"

        system_prompt = """
你是一个合规的医疗报告信息整理助手。请严格遵守以下规则：

1. 核心规则（必须遵守）：
   - 仅整理和复述实际的检查项目和检测数值，绝不添加任何原文没有的内容
   - 严禁进行任何医学诊断、病情判断或健康评估
   - 严禁对指标是否正常做出结论
   - 严禁建议任何治疗、用药、就医行为
   - 严禁解释各项指标代表的临床意义
   - 仅做客观的文字整理，保持中立

2. 语言要求：
   - 所有输出必须使用纯中文

3. 输出格式（必须严格遵守）：
   第一部分：报告基本信息概述
   - 简述报告类型
   - 概括检测项目数量

   第二部分：检测数据整理
   - 以结构化方式列出各项检测指标的名称、检测数值和参考范围
   - 不对数值做任何评判

   第三部分：合规声明（必须包含以下三段内容，不得省略任何一段）：
   【重要说明】以上内容仅为对检测报告的客观转录和整理，不包含任何医学分析、诊断或评估。
   【合规声明】本系统不提供医疗诊断或治疗建议，所有检测指标的临床意义需由执业医师结合患者实际情况进行综合判断。
   【就医提示】如需了解检测结果的临床意义，请携带本报告前往正规医疗机构，咨询专业医生。请勿自行解读或根据网络信息做出健康决策。
"""

        user_prompt = f"报告类型：{report_type}\n\n报告原文转录内容：\n{report_description}\n\n请按照规定的格式整理上述报告数据。"

        data = {
            "model": settings.OLLAMA_MODEL,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "max_tokens": 2000
            }
        }

        response = requests.post(url, json=data, timeout=120)

        if response.status_code == 200:
            result = response.json()
            raw_response = result.get("response", "").strip()
            validated = validate_report_interpretation(raw_response)
            return validated
        else:
            return generate_fallback_interpretation(report_description, report_type)

    except Exception as e:
        print(f"报告解读生成异常: {e}")
        return generate_fallback_interpretation(report_description, report_type)

def validate_report_interpretation(text):
    for keyword in MEDICAL_DIAGNOSIS_BLOCKLIST:
        if keyword in text:
            text = text.replace(keyword, "***")

    required_disclaimers = [
        "【重要说明】",
        "【合规声明】",
        "【就医提示】",
    ]

    missing = [d for d in required_disclaimers if d not in text]

    if missing:
        text += "\n\n【重要说明】以上内容仅为对检测报告的客观转录和整理，不包含任何医学分析、诊断或评估。"
        text += "\n【合规声明】本系统不提供医疗诊断或治疗建议，所有检测指标的临床意义需由执业医师结合患者实际情况进行综合判断。"
        text += "\n【就医提示】如需了解检测结果的临床意义，请携带本报告前往正规医疗机构，咨询专业医生。请勿自行解读或根据网络信息做出健康决策。"

    return text

def generate_fallback_interpretation(report_description, report_type):
    result = f"报告类型：{report_type}\n\n"
    result += "检测数据整理：\n"
    result += report_description[:1500] if len(report_description) > 1500 else report_description
    result += "\n\n【重要说明】以上内容仅为对检测报告的客观转录和整理，不包含任何医学分析、诊断或评估。"
    result += "\n【合规声明】本系统不提供医疗诊断或治疗建议，所有检测指标的临床意义需由执业医师结合患者实际情况进行综合判断。"
    result += "\n【就医提示】如需了解检测结果的临床意义，请携带本报告前往正规医疗机构，咨询专业医生。请勿自行解读或根据网络信息做出健康决策。"
    return result

def generate_structured_data(report_description, report_type):
    structured = {
        "报告类型": report_type,
        "转录内容": report_description[:1000] if report_description else ""
    }
    return json.dumps(structured, ensure_ascii=False)

def compute_image_hash(image_base64):
    try:
        image_bytes = base64.b64decode(image_base64)
        return hashlib.sha256(image_bytes).hexdigest()
    except Exception:
        return None

def cleanup_temp_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"清理临时文件失败: {e}")

def is_report_compliant(text):
    for keyword in MEDICAL_DIAGNOSIS_BLOCKLIST:
        if keyword in text:
            return False, f"输出包含违规内容：{keyword}"
    return True, "合规"
