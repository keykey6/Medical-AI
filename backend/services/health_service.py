import json
import base64
import requests

from config import settings

OLLAMA_URL = f"{settings.OLLAMA_BASE_URL}/api/generate"
OLLAMA_MODEL = settings.OLLAMA_MODEL
MULTIMODAL_MODEL = settings.OLLAMA_MULTIMODAL_MODEL

DISCLAIMER = "\n\n【免责声明】以上内容仅供健康科普参考，不构成医疗诊断或治疗建议。如有健康疑虑，请及时前往正规医疗机构就诊，咨询专业医生。"

HEALTH_KNOWLEDGE = {
    "糖尿病有哪些症状？": "糖尿病的常见症状包括：多饮（口渴频繁饮水）、多尿（排尿次数和量增多）、多食、体重下降、疲乏无力、视力模糊、伤口愈合缓慢等。部分2型糖尿病患者早期可能无明显症状。如出现上述情况，建议前往医院进行血糖检测。",
    "如何预防胃酸反流？": "预防胃酸反流的常见方式包括：少食多餐、避免过饱、饭后不要立即躺下（至少保持直立2-3小时）、减少高脂肪和辛辣食物摄入、控制体重、戒烟限酒、抬高床头等。如症状频繁且严重，建议前往消化内科就诊。",
    "高血压注意事项": "高血压患者应注意：定期监测血压、低盐低脂饮食（每日食盐不超过6克）、规律运动（每周至少150分钟中等强度运动）、保持健康体重、戒烟限酒、避免情绪波动、遵医嘱服药并定期复诊。高血压管理需长期坚持。",
    "健康饮食建议": "健康饮食的核心包括：摄入多种多样的食物（谷薯类、蔬菜水果、肉蛋奶豆类）、控制油盐糖摄入、每日保证足量饮水、少食多餐细嚼慢咽。蔬菜每日摄入300-500克，水果200-350克。均衡营养是保持身体健康的基础。",
    "运动健康指南": "成年人建议每周进行至少150分钟中等强度有氧运动（如快走、慢跑、游泳等）和2次力量训练。运动前应充分热身，运动后做拉伸放松。根据自身情况选择合适运动强度，避免过度运动。如有关节等基础疾病，建议在专业人员指导下进行。",
    "失眠怎么办？": "改善睡眠的建议包括：保持规律的作息时间、睡前避免使用电子产品、避免咖啡因和酒精摄入、营造舒适的睡眠环境（安静、暗光、适宜温度）、睡前可以尝试冥想或深呼吸放松。如果长期失眠严重影响生活，建议咨询睡眠专科医生。",
}

FOOD_KNOWLEDGE = {
    "米饭": "米饭是主要的主食来源，富含碳水化合物，提供能量。每100克约含热量116大卡。建议搭配蔬菜和蛋白质食物一起食用，控制每餐主食量（一碗约150克）。粗粮米饭营养价值更高。",
    "面条": "面条同样是重要的主食选择，提供碳水化合物和能量。建议搭配蔬菜和蛋白质，避免过于油腻的调味。选择全麦面条可增加膳食纤维摄入。",
    "苹果": "苹果富含维生素C和膳食纤维，有助于肠道健康。建议每日摄入1-2个，连皮食用效果更佳（充分清洗后）。苹果热量较低，适合作为日常水果选择。",
    "香蕉": "香蕉富含钾元素和碳水化合物，可快速补充能量。适合运动前后食用。每日建议1-2根。香蕉含有色氨酸，有助于改善情绪。",
    "西蓝花": "西蓝花是营养价值很高的蔬菜，富含维生素C、维生素K和膳食纤维，以及具有抗氧化作用的硫化物。建议清蒸或快炒，避免过度烹饪。",
    "鸡蛋": "鸡蛋是优质蛋白质来源，含有全部必需氨基酸。每日建议摄入1-2个。蛋黄含有胆固醇，但适量摄入对健康人群无明显负面影响。建议水煮或少油烹饪。",
    "牛奶": "牛奶是钙质和蛋白质的重要来源。成年人每日建议摄入300-500毫升。乳糖不耐受人群可选择酸奶或乳糖分解牛奶作为替代。",
    "鱼肉": "鱼类是优质蛋白质来源，深海鱼富含不饱和脂肪酸（如三文鱼、沙丁鱼）。建议每周食用2-3次鱼类，蒸煮为佳，减少油炸。",
}

MEDICATION_KNOWLEDGE = {
    "阿莫西林": "阿莫西林是一种青霉素类抗生素，主要用于细菌感染。必须在医生处方下使用，严禁自行购买服用。滥用抗生素可能导致耐药性。使用前需确认无青霉素过敏史。",
    "布洛芬": "布洛芬是非甾体抗炎药，具有解热镇痛作用。不可长期使用，有胃溃疡、肾功能不全者慎用。请严格按照药品说明书或医嘱服用。",
    "对乙酰氨基酚": "对乙酰氨基酚是常用解热镇痛药物，对胃肠道刺激较小。不可超量服用，每日总量不超过2克。过量可能导致肝损伤。",
    "阿司匹林": "阿司匹林具有抗血小板聚集作用，用于心脑血管疾病的预防。需在医生指导下使用。有出血风险、胃溃疡者慎用。儿童病毒感染期间禁用。",
    "头孢类": "头孢类抗生素是常用的广谱抗菌药物，有多种类型，必须由医生处方使用。使用前后一周内严禁饮酒。有青霉素过敏史者需告知医生。",
}


def analyze_food_image(image_base64, additional_text=None):
    try:
        prompt = "请识别并描述图片中的食物种类、主要食材和烹饪方式。仅做客观描述，不进行任何医疗或营养评估。"
        if additional_text:
            prompt = f"用户补充说明：{additional_text}\n\n{prompt}"

        data = {
            "model": MULTIMODAL_MODEL,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {"temperature": 0.0, "max_tokens": 800}
        }

        response = requests.post(OLLAMA_URL, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            description = result.get("response", "").strip()
            return generate_food_advice(description)
        return "食物识别失败，请确认图片清晰后重试。"

    except Exception as e:
        print(f"食物分析异常: {e}")
        return "食物分析服务暂时不可用，请稍后重试。"


def generate_food_advice(food_description):
    matched = []
    for keyword, info in FOOD_KNOWLEDGE.items():
        if keyword in food_description:
            matched.append(f"【{keyword}】{info}")

    if not matched:
        matched.append(f"识别到的食物：{food_description}")

    result = "食物分析结果：\n\n"
    result += "\n\n".join(matched)

    advice = "\n\n饮食建议（仅供参考）："
    advice += "\n- 保持饮食多样化，均衡摄入各类营养素"
    advice += "\n- 控制每餐分量，避免暴饮暴食"
    advice += "\n- 注意烹饪方式，蒸煮优于油炸"
    advice += DISCLAIMER
    return result + advice


def generate_tcm_knowledge(query):
    try:
        system_prompt = """
你是一个中医药文化科普助手。请严格遵守以下规则：

1. 你只能提供中医药传统文化知识、养生理念的一般性科普介绍
2. 严禁进行中医辨证诊断（如"阴虚""阳虚"等）  
3. 严禁开具任何中药处方或推荐具体方剂
4. 严禁推荐任何中药材的用法用量
5. 严禁声称任何中药或养生方法能够治疗疾病
6. 仅介绍中医药的基本概念、养生理念和历史背景

所有回答必须以以下声明结尾：
"以上内容仅为中医药传统文化知识科普，不构成任何诊疗建议。如需中医诊疗，请前往正规中医医疗机构，由执业中医师进行辨证施治。"
"""

        data = {
            "model": OLLAMA_MODEL,
            "prompt": query,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": 0.3, "max_tokens": 1500}
        }

        response = requests.post(OLLAMA_URL, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            text = result.get("response", "").strip()
            if "以上内容仅为中医药传统文化知识科普" not in text:
                text += "\n\n以上内容仅为中医药传统文化知识科普，不构成任何诊疗建议。如需中医诊疗，请前往正规中医医疗机构，由执业中医师进行辨证施治。"
            return text
        return "中医咨询服务暂时不可用，请稍后重试。"

    except Exception as e:
        print(f"中医咨询异常: {e}")
        return "中医咨询服务暂时不可用，请稍后重试。"


def analyze_medication_image(image_base64):
    """Use multimodal model to read medicine info from packaging/instructions/pill photo."""
    try:
        prompt = """请仔细观察这张药品图片（可能是药品包装盒、说明书或药片本身），提取以下信息：
1. 药品通用名称
2. 如果有的话，生产厂家
3. 如果是药片，描述药片的外观特征

只提取可见的文字信息，不要编造任何信息。请用中文回答。"""

        data = {
            "model": MULTIMODAL_MODEL,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {"temperature": 0.0, "max_tokens": 600}
        }

        response = requests.post(OLLAMA_URL, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            extracted = result.get("response", "").strip()
            if not extracted:
                return "未能从图片中识别到药品信息，请确保图片清晰可见。"

            # Try to match extracted text against medication knowledge base
            matched = None
            for keyword, info in MEDICATION_KNOWLEDGE.items():
                if keyword in extracted:
                    matched = (keyword, info)
                    break

            text = "图片识别结果：\n" + extracted + "\n\n"

            if matched:
                text += f"药品科普信息：\n\n【{matched[0]}】\n{matched[1]}\n\n"

            text += "【重要提醒】以上为图片识别及药品基础知识科普。"
            text += "用药请严格遵医嘱，切勿自行购药或调整用量。"
            text += "图片识别可能存在误差，请以实物包装及说明书为准。"
            return text

        return "药品图片识别失败，请确认图片清晰后重试。"

    except Exception as e:
        print(f"药品图片分析异常: {e}")
        return "药品图片识别服务暂时不可用，请稍后重试。"


def lookup_medication(query):
    for keyword, info in MEDICATION_KNOWLEDGE.items():
        if keyword in query:
            return f"药品科普信息：\n\n药品名称：{keyword}\n{info}\n\n【重要提醒】以上为药品基础知识科普，不构成任何用药建议。用药请严格遵守医嘱，切勿自行购药或调整用量。如有用药疑问，请咨询执业医师或药师。"

    try:
        system_prompt = """
你是一个药品基础知识科普助手。请严格遵守以下规则：

1. 你只能提供药品的通用名称、基本分类、一般作用机理等公共知识
2. 严禁任何药品推荐、用法用量建议
3. 严禁声称任何药品可以治疗某种疾病
4. 严禁对比不同药品的优劣
5. 如不确定药品信息，请坦诚告知

所有回答必须包含以下声明：
"以上为药品基础知识科普，不构成用药建议。请严格在医生指导下使用药品。如有用药疑问，请咨询执业医师或药师。"
"""

        data = {
            "model": OLLAMA_MODEL,
            "prompt": query,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": 0.2, "max_tokens": 1000}
        }

        response = requests.post(OLLAMA_URL, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            text = result.get("response", "").strip()
            if "以上为药品基础知识科普" not in text:
                text += "\n\n以上为药品基础知识科普，不构成用药建议。请严格在医生指导下使用药品。如有用药疑问，请咨询执业医师或药师。"
            return text
        return "药品信息查询失败，请稍后重试。"

    except Exception as e:
        print(f"药品查询异常: {e}")
        return "药品信息查询服务暂时不可用，请稍后重试。"


def search_hospitals(query):
    try:
        system_prompt = """
你是一个医院及科室信息科普助手。请严格遵守以下规则：

1. 仅提供医院科室设置、挂号流程等公共信息服务
2. 严禁推荐或评价任何特定医院或医生
3. 严禁声称某个医院或科室比其他更好
4. 严禁对医疗水平、治疗方案做任何评价

所有回答必须包含以下声明：
"以上信息仅供就医参考，具体医院和医生选择请根据自身情况综合判断。建议通过正规渠道（如医院官网、卫健委官网）获取最新信息。"
"""

        data = {
            "model": OLLAMA_MODEL,
            "prompt": query,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": 0.2, "max_tokens": 1200}
        }

        response = requests.post(OLLAMA_URL, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            text = result.get("response", "").strip()
            if "以上信息仅供就医参考" not in text:
                text += "\n\n以上信息仅供就医参考，具体医院和医生选择请根据自身情况综合判断。建议通过正规渠道获取最新信息。"
            return text
        return "医院信息查询失败，请稍后重试。"

    except Exception as e:
        print(f"医院搜索异常: {e}")
        return "医院信息查询服务暂时不可用，请稍后重试。"


def generate_health_assessment(profile):
    if not profile:
        return "请先完善健康档案信息后再进行评估。"

    tips = []

    try:
        bmi = None
        height_val = profile.get('height')
        weight_val = profile.get('weight')
        if height_val and weight_val and height_val > 0:
            height_m = float(height_val) / 100
            weight_kg = float(weight_val)
            bmi = round(weight_kg / (height_m * height_m), 1)

        if bmi:
            tips.append(f"您当前的体质指数约为 {bmi}。")

        if profile.get('allergies'):
            tips.append(f"已记录过敏史：{profile['allergies']}。在日常生活中应注意避免接触过敏原。")

        if profile.get('diseases'):
            tips.append(f"已记录既往疾病史。建议定期复诊，遵医嘱管理健康。")

        tips.append("\n日常健康建议：")
        tips.append("- 均衡饮食，多摄入蔬菜水果")
        tips.append("- 每周至少进行150分钟中等强度运动")
        tips.append("- 保持充足的睡眠（7-8小时/天）")
        tips.append("- 保持良好心态，避免长期压力")
        tips.append("- 定期体检，关注身体状况")

        tips.append(DISCLAIMER)

        return "\n".join(tips)

    except Exception as e:
        print(f"健康评估异常: {e}")
        return "健康评估暂时不可用，请稍后重试。"


def get_lifestyle_advice(category, profile=None):
    """Get lifestyle advice. If profile is provided, use LLM for personalized advice."""

    if profile:
        return _get_personalized_lifestyle_advice(category, profile)

    advices = {
        "饮食": "健康饮食建议：\n\n1. 均衡摄入各类食物：谷薯类、蔬菜水果、肉蛋奶豆类\n2. 每日蔬菜摄入300-500克，水果200-350克\n3. 控制食盐摄入，每日不超过6克\n4. 减少高糖、高脂肪食物的摄入\n5. 每日饮水量建议1500-2000毫升\n6. 少食多餐，细嚼慢咽\n7. 多吃粗粮杂粮，减少精白米面",
        "运动": "科学运动建议：\n\n1. 每周至少150分钟中等强度有氧运动\n2. 每周2-3次力量训练\n3. 运动前充分热身5-10分钟\n4. 运动后做拉伸放松\n5. 选择适合自己的运动方式（快走、游泳、太极等）\n6. 循序渐进，避免突然增加运动强度\n7. 如有关节或心血管疾病，请在专业人员指导下运动",
        "睡眠": "改善睡眠建议：\n\n1. 保持规律的作息时间，固定上床和起床时间\n2. 睡前1小时避免使用手机、电脑等电子产品\n3. 睡前避免咖啡、浓茶和酒精\n4. 营造舒适的睡眠环境（暗光、安静、温度适宜）\n5. 白天适当运动有助于夜间睡眠\n6. 睡前可尝试冥想、深呼吸等放松方法",
        "心理": "心理健康维护：\n\n1. 保持积极乐观的心态\n2. 学会压力管理，适当放松\n3. 保持良好的人际关系和社会支持\n4. 培养兴趣爱好\n5. 遇到困难时及时寻求帮助\n6. 必要时可咨询专业心理咨询师",
    }

    result = advices.get(category, "请选择饮食、运动、睡眠或心理类别查询。")
    if category in ("饮食", "运动", "睡眠"):
        result += "\n\n💡 登录并完善健康档案后，可获得基于您个人情况的个性化建议。"
    return result + DISCLAIMER


def _get_personalized_lifestyle_advice(category, profile):
    """Use LLM to generate personalized lifestyle advice based on health profile."""
    name = profile.get('name', '用户')
    gender = profile.get('gender', '未填写')
    age = profile.get('age', '未填写')
    height = profile.get('height', '未填写')
    weight = profile.get('weight', '未填写')
    allergies = profile.get('allergies', '无')
    diseases = profile.get('diseases', '无')
    medications = profile.get('medications', '无')

    profile_text = f"""用户健康档案：
- 性别：{gender}
- 年龄：{age}
- 身高：{height}cm
- 体重：{weight}kg
- 过敏史：{allergies}
- 既往病史：{diseases}
- 当前用药：{medications}"""

    category_prompts = {
        "饮食": f"""请根据以下用户健康档案，提供个性化的饮食建议。

{profile_text}

请从以下几个方面给出建议：
1. 根据用户的年龄、体重和病史，推荐适合的食物类型和营养搭配
2. 需要特别注意的饮食禁忌（结合过敏史和病史）
3. 一日三餐的参考搭配建议
4. 与当前用药可能相关的饮食注意事项

要求：建议需具体实用，结合用户实际情况。严禁声称可以治疗疾病。""",

        "运动": f"""请根据以下用户健康档案，提供个性化的运动建议。

{profile_text}

请从以下几个方面给出建议：
1. 根据用户的年龄和身体状况，推荐适合的运动类型和强度
2. 每周运动频率和时长建议
3. 运动时的注意事项（结合病史）
4. 不适合的运动类型

要求：建议需具体实用，结合用户实际情况。严禁声称可以治疗疾病。""",

        "睡眠": f"""请根据以下用户健康档案，提供个性化的睡眠改善建议。

{profile_text}

请从以下几个方面给出建议：
1. 根据用户的年龄和身体状况，分析可能的睡眠影响因素
2. 改善睡眠质量的具体方法
3. 睡前习惯和环境优化建议
4. 当前用药可能对睡眠的影响分析

要求：建议需具体实用，结合用户实际情况。严禁声称可以治疗疾病。""",

        "心理": f"""请根据以下用户健康档案，提供个性化的心理调适建议。

{profile_text}

请从以下几个方面给出建议：
1. 结合用户的健康状况，分析可能面临的心理压力
2. 压力管理和情绪调节的具体方法
3. 日常生活中可以实践的心理健康习惯
4. 何时需要寻求专业心理咨询的建议

要求：建议需具体实用，结合用户实际情况。严禁声称可以治疗疾病。""",
    }

    prompt = category_prompts.get(category)
    if not prompt:
        return get_lifestyle_advice(category)

    try:
        data = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": f"""你是一个专业的健康生活方式指导助手。请严格遵守以下规则：

1. 你只能提供基于用户健康档案的健康生活方式建议
2. 建议必须结合用户的具体情况（年龄、体重、病史等）
3. 严禁进行疾病诊断或声称可以治疗疾病
4. 严禁开具处方或推荐具体药物
5. 涉及用药问题时，提醒用户咨询医生
6. 所有建议均为科普性质，不构成医疗建议

用户称呼为：{name}""",
            "stream": False,
            "options": {"temperature": 0.3, "max_tokens": 1500}
        }

        response = requests.post(OLLAMA_URL, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            text = result.get("response", "").strip()
            if text:
                text += "\n\n---\n以上建议基于您填写的健康档案生成，为个性化科普内容。"
                text += DISCLAIMER
                return text

        # Fallback to generic advice
        return get_lifestyle_advice(category)

    except Exception as e:
        print(f"个性化建议生成异常: {e}")
        return get_lifestyle_advice(category)


def get_health_knowledge(query):
    for keyword, info in HEALTH_KNOWLEDGE.items():
        if query.strip() == keyword or keyword in query:
            return info + DISCLAIMER

    for keyword, info in HEALTH_KNOWLEDGE.items():
        if any(w in query for w in keyword.split("？")[0].split("如何")[-1].split("怎么办")[0] if len(w) >= 2):
            return info + DISCLAIMER

    return None
