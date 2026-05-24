import os
import json
import requests
import hashlib
from config import settings

OLLAMA_URL = f"{settings.OLLAMA_BASE_URL}/api/generate"
OLLAMA_MODEL = settings.OLLAMA_MODEL
BAIDU_AK = settings.BAIDU_MAP_AK
BAIDU_SERVER_AK = settings.BAIDU_MAP_SERVER_AK or settings.BAIDU_MAP_AK

DISCLAIMER_HOSPITAL = "\n\n【免责声明】以上医院信息来源于公开数据，仅供参考。不构成对任何医院的推荐或评价。就医请咨询专业医生，并通过官方渠道确认医院资质和科室信息。本系统不提供挂号或在线问诊服务。"

CHINA_HOSPITALS = {
    "北京": [
        {"name": "北京协和医院", "address": "北京市东城区帅府园1号", "phone": "010-69156114", "level": "三级甲等", "departments": ["内科", "外科", "妇产科", "儿科", "骨科", "皮肤科", "眼科", "耳鼻喉科", "心血管内科", "神经内科", "内分泌科", "风湿免疫科", "血液科", "泌尿外科", "神经外科", "胸外科", "整形外科", "肿瘤科", "口腔科", "中医科"], "lat": 39.9128, "lng": 116.4107, "desc": "大型综合性三级甲等医院，国家卫生健康委指定的全国疑难重症诊治指导中心"},
        {"name": "北京大学第一医院", "address": "北京市西城区西什库大街8号", "phone": "010-83572211", "level": "三级甲等", "departments": ["内科", "外科", "妇产科", "儿科", "骨科", "皮肤科", "眼科", "耳鼻喉科", "神经内科", "心血管内科", "肾内科", "泌尿外科", "消化内科", "呼吸内科"], "lat": 39.9256, "lng": 116.3698, "desc": "集医疗、教学、科研为一体的大型综合性三甲医院，北大医学部直属"},
        {"name": "北京医院", "address": "北京市东城区东单大华路1号", "phone": "010-85132266", "level": "三级甲等", "departments": ["内科", "外科", "骨科", "心血管内科", "神经内科", "内分泌科", "老年病科", "妇产科", "眼科", "耳鼻喉科"], "lat": 39.9090, "lng": 116.4220, "desc": "以老年病、慢性病诊疗为特色的大型综合性三甲医院"},
        {"name": "北京大学人民医院", "address": "北京市西城区西直门南大街11号", "phone": "010-88326666", "level": "三级甲等", "departments": ["内科", "外科", "骨科", "血液科", "心脏中心", "妇产科", "儿科", "眼科", "风湿免疫科", "泌尿外科"], "lat": 39.9365, "lng": 116.3578, "desc": "以疑难危重症诊疗为特色的综合性三甲医院"},
        {"name": "北京朝阳医院", "address": "北京市朝阳区工人体育场南路8号", "phone": "010-85231000", "level": "三级甲等", "departments": ["呼吸内科", "心血管内科", "骨科", "泌尿外科", "妇产科", "儿科", "急诊科", "神经内科", "消化内科"], "lat": 39.9269, "lng": 116.4532, "desc": "以呼吸与危重症医学、器官移植为特色的三甲医院"},
    ],
    "上海": [
        {"name": "上海交通大学医学院附属瑞金医院", "address": "上海市黄浦区瑞金二路197号", "phone": "021-64370045", "level": "三级甲等", "departments": ["内科", "外科", "妇产科", "儿科", "骨科", "皮肤科", "内分泌科", "血液科", "心血管内科", "神经内科", "泌尿外科", "消化内科", "呼吸内科", "烧伤科"], "lat": 31.2119, "lng": 121.4661, "desc": "全国知名的大型综合性三甲医院，内分泌、血液学科全国领先"},
        {"name": "复旦大学附属中山医院", "address": "上海市徐汇区枫林路180号", "phone": "021-64041990", "level": "三级甲等", "departments": ["内科", "外科", "骨科", "心血管内科", "肝肿瘤科", "呼吸内科", "泌尿外科", "妇产科", "眼科"], "lat": 31.1987, "lng": 121.4521, "desc": "以心血管、肝肿瘤诊疗为特色的综合性三甲医院"},
        {"name": "复旦大学附属华山医院", "address": "上海市静安区乌鲁木齐中路12号", "phone": "021-52889999", "level": "三级甲等", "departments": ["神经内科", "神经外科", "皮肤科", "手外科", "感染科", "运动医学科", "骨科", "内科", "外科"], "lat": 31.2180, "lng": 121.4476, "desc": "以神经内外科、皮肤科、感染科著称的著名三甲医院"},
        {"name": "上海交通大学医学院附属仁济医院", "address": "上海市浦东新区浦建路160号", "phone": "021-58752345", "level": "三级甲等", "departments": ["消化内科", "风湿免疫科", "泌尿外科", "妇产科", "心内科", "神经外科", "骨科", "普外科"], "lat": 31.2063, "lng": 121.5186, "desc": "以消化病学为特色的综合性三甲医院，在浦东有多院区"},
        {"name": "上海市第一人民医院", "address": "上海市虹口区武进路85号", "phone": "021-63240090", "level": "三级甲等", "departments": ["眼科", "泌尿外科", "骨科", "心血管内科", "妇产科", "消化内科", "呼吸内科", "急诊科"], "lat": 31.2572, "lng": 121.4856, "desc": "上海历史悠久的综合性三甲医院，眼科、泌尿科实力突出"},
    ],
    "广州": [
        {"name": "中山大学附属第一医院", "address": "广州市越秀区中山二路58号", "phone": "020-87755766", "level": "三级甲等", "departments": ["内科", "外科", "妇产科", "儿科", "骨科", "神经内科", "心血管内科", "泌尿外科", "消化内科", "肾内科", "器官移植科"], "lat": 23.1292, "lng": 113.2878, "desc": "华南地区最具影响力的综合性三甲医院之一"},
        {"name": "南方医科大学南方医院", "address": "广州市白云区广州大道北1838号", "phone": "020-61641888", "level": "三级甲等", "departments": ["消化内科", "肾内科", "骨科", "心血管内科", "妇产科", "儿科", "血液科", "感染科"], "lat": 23.1790, "lng": 113.3363, "desc": "以消化病学、肾脏病学为优势学科的综合性三甲医院"},
        {"name": "广东省人民医院", "address": "广州市越秀区中山二路106号", "phone": "020-83827812", "level": "三级甲等", "departments": ["心血管内科", "心血管外科", "老年病科", "肿瘤科", "骨科", "妇产科", "神经内科", "呼吸内科"], "lat": 23.1296, "lng": 113.2908, "desc": "以心血管疾病诊疗为龙头的省级大型综合性三甲医院"},
        {"name": "广州市第一人民医院", "address": "广州市越秀区盘福路1号", "phone": "020-81048888", "level": "三级甲等", "departments": ["消化内科", "妇产科", "骨科", "普外科", "泌尿外科", "眼科", "耳鼻喉科", "心血管内科"], "lat": 23.1331, "lng": 113.2574, "desc": "广州市属大型综合性三甲医院，消化病学为优势学科"},
    ],
    "深圳": [
        {"name": "北京大学深圳医院", "address": "深圳市福田区莲花路1120号", "phone": "0755-83923333", "level": "三级甲等", "departments": ["内科", "外科", "骨科", "妇产科", "儿科", "心血管内科", "神经内科", "皮肤科", "眼科", "口腔科"], "lat": 22.5572, "lng": 114.0500, "desc": "北大与深圳合作建设的大型综合性三甲医院"},
        {"name": "深圳市人民医院", "address": "深圳市罗湖区东门北路1017号", "phone": "0755-25533018", "level": "三级甲等", "departments": ["内科", "外科", "妇产科", "儿科", "骨科", "神经内科", "心血管内科", "呼吸内科", "泌尿外科", "口腔科"], "lat": 22.5462, "lng": 114.1262, "desc": "深圳最早的综合性三甲医院，深圳大学附属医院"},
        {"name": "深圳市第二人民医院", "address": "深圳市福田区笋岗西路3002号", "phone": "0755-83366388", "level": "三级甲等", "departments": ["神经外科", "骨科", "烧伤科", "内科", "外科", "妇产科", "儿科", "眼科"], "lat": 22.5567, "lng": 114.0772, "desc": "深圳综合性三甲医院，以神经外科和骨科为优势学科"},
    ],
    "杭州": [
        {"name": "浙江大学医学院附属第一医院", "address": "杭州市上城区庆春路79号", "phone": "0571-87236114", "level": "三级甲等", "departments": ["内科", "外科", "妇产科", "儿科", "骨科", "感染科", "心血管内科", "泌尿外科", "肿瘤科", "器官移植科"], "lat": 30.2564, "lng": 120.1732, "desc": "浙江省规模最大的综合性三甲医院，浙大医学院直属"},
        {"name": "浙江大学医学院附属第二医院", "address": "杭州市上城区解放路88号", "phone": "0571-87783777", "level": "三级甲等", "departments": ["心血管内科", "骨科", "眼科", "神经内科", "内科", "外科", "烧伤科", "急诊科"], "lat": 30.2452, "lng": 120.1701, "desc": "以心血管、骨科为特色的著名综合性三甲医院"},
    ],
    "武汉": [
        {"name": "华中科技大学同济医学院附属同济医院", "address": "武汉市硚口区解放大道1095号", "phone": "027-83662688", "level": "三级甲等", "departments": ["内科", "外科", "妇产科", "儿科", "骨科", "心血管内科", "神经内科", "泌尿外科", "肿瘤科", "器官移植科", "妇产科"], "lat": 30.5822, "lng": 114.2625, "desc": "华中地区影响力最大的综合性三甲医院之一"},
        {"name": "华中科技大学同济医学院附属协和医院", "address": "武汉市江汉区解放大道1277号", "phone": "027-85726114", "level": "三级甲等", "departments": ["内科", "外科", "心血管内科", "血液科", "泌尿外科", "妇产科", "儿科", "骨科", "眼科", "耳鼻喉科"], "lat": 30.5905, "lng": 114.2737, "desc": "以心血管和血液学科著称的大型综合性三甲医院"},
    ],
    "成都": [
        {"name": "四川大学华西医院", "address": "成都市武侯区国学巷37号", "phone": "028-85422114", "level": "三级甲等", "departments": ["内科", "外科", "骨科", "心血管内科", "神经内科", "泌尿外科", "妇产科", "儿科", "肿瘤科", "消化内科", "呼吸内科", "精神科"], "lat": 30.6427, "lng": 104.0636, "desc": "西南地区规模最大、实力最强的综合性三甲医院"},
        {"name": "四川省人民医院", "address": "成都市青羊区一环路西二段32号", "phone": "028-87393999", "level": "三级甲等", "departments": ["内科", "外科", "骨科", "妇产科", "心内科", "神经内科", "呼吸内科", "眼科", "耳鼻喉科"], "lat": 30.6608, "lng": 104.0369, "desc": "四川省大型综合性三甲医院"},
    ],
}

ALL_DEPARTMENTS = [
    "内科", "外科", "妇产科", "儿科", "骨科", "眼科", "耳鼻喉科", "口腔科",
    "心血管内科", "神经内科", "消化内科", "呼吸内科", "肾内科", "内分泌科",
    "泌尿外科", "神经外科", "胸外科", "整形外科", "烧伤科",
    "皮肤科", "肿瘤科", "血液科", "风湿免疫科", "感染科",
    "急诊科", "老年病科", "中医科", "精神科",
    "器官移植科", "心脏中心", "肝肿瘤科", "手外科", "运动医学科"
]

ALL_LEVELS = ["三级甲等", "三级乙等", "二级甲等", "二级乙等", "一级甲等"]


def get_hospital_builtin(lat=None, lng=None, city=None, department=None, level=None, keyword=None):
    results = []

    for city_name, hospitals in CHINA_HOSPITALS.items():
        for h in hospitals:
            if city and city not in city_name and city_name not in city:
                continue
            if level and level != h["level"]:
                continue
            if department:
                dept_match = False
                for d in h["departments"]:
                    if department in d:
                        dept_match = True
                        break
                if not dept_match:
                    continue
            if keyword:
                kw_match = keyword in h["name"] or keyword in h["desc"]
                for d in h["departments"]:
                    if keyword in d:
                        kw_match = True
                        break
                if not kw_match:
                    continue

            if lat and lng:
                dist = ((h["lat"] - float(lat)) ** 2 + (h["lng"] - float(lng)) ** 2) ** 0.5
            else:
                dist = 0

            results.append({
                "name": h["name"],
                "address": h["address"],
                "phone": h["phone"],
                "level": h["level"],
                "departments": h["departments"],
                "desc": h["desc"],
                "lat": h["lat"],
                "lng": h["lng"],
                "distance": round(dist * 111, 1),
                "city": city_name
            })

    if lat and lng:
        results.sort(key=lambda x: x["distance"])

    return results


def search_all_hospitals(department=None, level=None, keyword=None, limit=20):
    results = []
    for city_name, hospitals in CHINA_HOSPITALS.items():
        for h in hospitals:
            if level and level != h["level"]:
                continue
            if department:
                dept_match = False
                for d in h["departments"]:
                    if department in d:
                        dept_match = True
                        break
                if not dept_match:
                    continue
            if keyword:
                kw_match = keyword in h["name"] or keyword in h["desc"]
                for d in h["departments"]:
                    if keyword in d:
                        kw_match = True
                        break
                if not kw_match:
                    continue

            results.append({
                "name": h["name"],
                "address": h["address"],
                "phone": h["phone"],
                "level": h["level"],
                "departments": h["departments"],
                "desc": h["desc"],
                "lat": h["lat"],
                "lng": h["lng"],
                "city": city_name
            })

    return results[:limit]


def get_departments():
    return ALL_DEPARTMENTS


def get_levels():
    return ALL_LEVELS


def get_supported_cities():
    return list(CHINA_HOSPITALS.keys())


def generate_hospital_response_with_llm(query, found_hospitals):
    try:
        hospital_context = "以下是根据查询找到的医院信息：\n"
        for i, h in enumerate(found_hospitals[:5]):
            hospital_context += f"\n{i+1}. {h['name']}（{h['level']}）\n"
            hospital_context += f"   地址：{h['address']}\n"
            hospital_context += f"   电话：{h['phone']}\n"
            hospital_context += f"   科室：{', '.join(h['departments'][:8])}\n"
            hospital_context += f"   简介：{h['desc']}\n"

        system_prompt = """
你是一个医院信息指引助手。请严格遵守以下规则：

1. 你只能基于提供的医院信息进行客观陈述和整理
2. 严禁对任何医院的医疗水平、医生技术进行评价或比较
3. 严禁推荐或贬低任何具体医院
4. 严禁声称哪个医院更好、哪个科室更强
5. 只能客观列出医院名称、地址、科室等基本信息

回答末尾必须包含以下声明：
"以上信息来源于公开数据，仅供参考。就医请咨询专业医生，并通过官方渠道确认医院资质。本系统不提供挂号或在线问诊服务。"
"""

        user_prompt = f"用户问题：{query}\n\n{hospital_context}\n请根据上述信息，为用户提供客观的就医指引，不推荐任何特定医院。"

        data = {
            "model": OLLAMA_MODEL,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": 0.2, "max_tokens": 1500}
        }

        response = requests.post(OLLAMA_URL, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            text = result.get("response", "").strip()
            if "以上信息来源于公开数据" not in text and "仅供参考" not in text:
                text += DISCLAIMER_HOSPITAL
            return text

        return generate_fallback_response(found_hospitals)

    except Exception as e:
        print(f"LLM医院回复异常: {e}")
        return generate_fallback_response(found_hospitals)


def generate_fallback_response(hospitals):
    if not hospitals:
        return "未找到匹配的医院信息。请尝试更换搜索条件。" + DISCLAIMER_HOSPITAL

    result = "找到以下医院信息：\n\n"
    for i, h in enumerate(hospitals[:5]):
        result += f"【{h['name']}】\n"
        result += f"等级：{h['level']}\n"
        result += f"地址：{h['address']}\n"
        result += f"电话：{h['phone']}\n"
        result += f"科室：{', '.join(h['departments'][:10])}\n"
        result += f"简介：{h['desc']}\n\n"

    result += DISCLAIMER_HOSPITAL
    return result


# ── Baidu Maps Web API ────────────────────────────────────────────────────

def baidu_place_search(query: str, region: str = "北京", lat: float = None, lng: float = None, radius: int = 5000, max_pages: int = 5) -> list:
    """Call Baidu Maps Place Search API to find hospitals. Fetches up to max_pages * 20 results."""
    if not BAIDU_SERVER_AK or BAIDU_SERVER_AK == "your_baidu_ak_here":
        return []

    url = "https://api.map.baidu.com/place/v2/search"
    all_results = []
    seen_names = set()

    for page in range(max_pages):
        params = {
            "query": query,
            "region": region,
            "output": "json",
            "ak": BAIDU_SERVER_AK,
            "scope": 2,
            "page_size": 20,
            "page_num": page,
        }
        if lat and lng:
            params["location"] = f"{lat},{lng}"
            params["radius"] = radius

        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get("status") != 0:
                break

            results = data.get("results", [])
            if not results:
                break

            for r in results:
                name = r.get("name", "").strip()
                if not name or name in seen_names:
                    continue
                seen_names.add(name)

                dist_val = r.get("detail_info", {}).get("distance", 0)
                if dist_val and lat and lng:
                    dist_km = round(dist_val / 1000, 1)
                elif lat and lng:
                    rlat = r.get("location", {}).get("lat", 0)
                    rlng = r.get("location", {}).get("lng", 0)
                    dist_km = round(((rlat - float(lat)) ** 2 + (rlng - float(lng)) ** 2) ** 0.5 * 111, 1)
                else:
                    dist_km = 0

                all_results.append({
                    "name": name,
                    "address": r.get("address", ""),
                    "phone": r.get("telephone", ""),
                    "level": r.get("detail_info", {}).get("tag", ""),
                    "departments": [],
                    "desc": r.get("detail_info", {}).get("overall_rating", ""),
                    "lat": r.get("location", {}).get("lat", 0),
                    "lng": r.get("location", {}).get("lng", 0),
                    "city": r.get("city", region),
                    "distance": dist_km,
                })

            if len(results) < 20:
                break
        except Exception as e:
            print(f"百度地图API调用失败 (page {page}): {e}")
            break

    return all_results


def get_baidu_ak() -> str:
    return BAIDU_AK
