SYMPTOM_KEYWORDS: dict[str, list[str]] = {
    '头痛': ['头痛', '头疼', '头胀', '头晕'],
    '发热': ['发烧', '发热', '体温高', '发冷'],
    '咳嗽': ['咳嗽', '干咳', '咳痰', '喉咙痒'],
    '腹痛': ['肚子疼', '腹痛', '胃疼', '肚子胀'],
    '胸痛': ['胸口疼', '胸痛', '胸闷', '心悸'],
    '关节痛': ['关节痛', '膝盖疼', '腰痛', '背痛'],
    '皮肤问题': ['皮疹', '皮肤痒', '红肿', '过敏'],
    '呼吸道': ['呼吸困难', '气喘', '鼻塞', '流涕'],
    '消化问题': ['恶心', '呕吐', '腹泻', '便秘'],
    '妇科': ['月经不调', '痛经', '白带异常', '怀孕'],
    '儿科': ['孩子', '宝宝', '婴儿', '儿童'],
    '眼科': ['眼睛疼', '视力模糊', '红眼', '干涩'],
    '耳鼻喉': ['耳朵疼', '耳鸣', '鼻塞', '喉咙痛'],
    '口腔科': ['牙疼', '牙龈出血', '口腔溃疡', '口臭']
}

DEPARTMENT_MAPPING: dict[str, list[str]] = {
    '头痛': ['神经内科', '急诊科'],
    '发热': ['发热门诊', '急诊科', '内科'],
    '咳嗽': ['呼吸内科', '急诊科'],
    '腹痛': ['消化内科', '急诊科', '普外科'],
    '胸痛': ['心内科', '急诊科', '呼吸内科'],
    '关节痛': ['骨科', '风湿免疫科'],
    '皮肤问题': ['皮肤科'],
    '呼吸道': ['呼吸内科', '急诊科'],
    '消化问题': ['消化内科'],
    '妇科': ['妇产科'],
    '儿科': ['儿科'],
    '眼科': ['眼科'],
    '耳鼻喉': ['耳鼻喉科'],
    '口腔科': ['口腔科']
}


def detect_symptoms(text: str) -> list[str]:
    detected: list[str] = []
    text = text.lower()

    for symptom, keywords in SYMPTOM_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                detected.append(symptom)
                break

    return detected


def triage_analysis(text: str) -> str | None:
    symptoms = detect_symptoms(text)

    if not symptoms:
        return None

    departments: set[str] = set()
    for symptom in symptoms:
        if symptom in DEPARTMENT_MAPPING:
            departments.update(DEPARTMENT_MAPPING[symptom])

    if not departments:
        return None

    response = "根据您描述的症状，建议您前往以下科室就诊：\n"
    for i, dept in enumerate(departments, 1):
        response += f"{i}. {dept}\n"

    response += "\n为了更好地帮助您，请您补充以下信息：\n"
    response += "1. 症状出现多久了？\n"
    response += "2. 是否有其他不适症状？\n"
    response += "3. 是否有既往病史？\n"
    response += "\n【温馨提示】以上仅为分诊建议，具体就诊科室请以医生诊断为准。"

    return response
