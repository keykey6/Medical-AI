from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import save_session, save_chat_log
from services.map_service import (
    get_hospital_builtin, search_all_hospitals, get_departments,
    get_levels, get_supported_cities, generate_hospital_response_with_llm,
    generate_fallback_response, DISCLAIMER_HOSPITAL,
    baidu_place_search, get_baidu_ak,
)
from services.compliance_service import filter_sensitive_words

map_router = APIRouter()


class HospitalSearchRequest(BaseModel):
    session_id: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    city: Optional[str] = None
    department: Optional[str] = None
    level: Optional[str] = None
    keyword: Optional[str] = None


class HospitalChatRequest(BaseModel):
    session_id: str
    query: str
    lat: Optional[float] = None
    lng: Optional[float] = None


class HospitalDetailRequest(BaseModel):
    name: str
    address: Optional[str] = None


@map_router.get("/departments")
async def get_all_departments():
    return {"departments": get_departments()}


@map_router.get("/levels")
async def get_all_levels():
    return {"levels": get_levels()}


@map_router.get("/cities")
async def get_all_cities():
    return {"cities": get_supported_cities()}


def _merge_hospitals(builtin: list, baidu: list) -> list:
    """Merge built-in and Baidu results, deduplicating by name."""
    seen = set()
    merged = []
    for h in builtin:
        key = h["name"].strip()
        if key not in seen:
            seen.add(key)
            h["source"] = "builtin"
            merged.append(h)
    for h in baidu:
        key = h["name"].strip()
        if key not in seen:
            seen.add(key)
            h["source"] = "baidu"
            merged.append(h)
    return merged


@map_router.post("/search")
async def search_hospitals(request: HospitalSearchRequest):
    save_session(request.session_id)

    keyword = filter_sensitive_words(request.keyword) if request.keyword else None

    # 1. Get built-in results
    if request.lat and request.lng:
        builtin = get_hospital_builtin(
            lat=request.lat, lng=request.lng, city=request.city,
            department=request.department, level=request.level, keyword=keyword
        )
    else:
        builtin = get_hospital_builtin(
            city=request.city, department=request.department,
            level=request.level, keyword=keyword
        )

    # 2. Enrich with Baidu Maps Place Search
    baidu_results = []
    search_region = request.city or "北京"
    search_query = keyword or request.department or "医院"
    if "医院" not in search_query:
        search_query += " 医院"

    try:
        baidu_results = baidu_place_search(
            query=search_query,
            region=search_region,
            lat=request.lat,
            lng=request.lng,
            max_pages=2,
        )
    except Exception:
        pass

    # 3. Merge and sort
    results = _merge_hospitals(builtin, baidu_results)
    if request.lat and request.lng:
        results.sort(key=lambda x: x.get("distance", 999))

    save_chat_log(
        request.session_id,
        f"[找医院-搜索] 城市:{search_region} 科室:{request.department or '不限'} 等级:{request.level or '不限'} 关键词:{keyword or '无'}",
        f"找到{len(results)}家医院 (内置{len(builtin)} + 百度{len(baidu_results)})",
        'hospital_search'
    )

    return {
        "session_id": request.session_id,
        "hospitals": results,
        "total": len(results),
        "disclaimer": "以上医院信息来源于公开数据，仅供参考。不构成对任何医院的推荐或评价。就医请咨询专业医生，并通过官方渠道确认医院资质。本系统不提供挂号或在线问诊服务。"
    }


@map_router.post("/nearby")
async def nearby_hospitals(request: HospitalSearchRequest):
    save_session(request.session_id)

    if not request.lat or not request.lng:
        raise HTTPException(status_code=400, detail="请提供经纬度位置信息")

    results = get_hospital_builtin(
        lat=request.lat, lng=request.lng, city=request.city,
        department=request.department, level=request.level
    )

    save_chat_log(
        request.session_id,
        f"[附近医院] lat:{request.lat} lng:{request.lng} 科室:{request.department or '不限'}",
        f"找到{len(results)}家附近医院",
        'nearby_hospital'
    )

    return {
        "session_id": request.session_id,
        "hospitals": results,
        "total": len(results),
        "center": {"lat": request.lat, "lng": request.lng},
        "disclaimer": "以上医院信息来源于公开数据，仅供参考。不构成对任何医院的推荐或评价。就医请咨询专业医生，并通过官方渠道确认医院资质。"
    }


@map_router.post("/chat")
async def hospital_chat(request: HospitalChatRequest):
    save_session(request.session_id)

    query = filter_sensitive_words(request.query)

    found = []
    if request.lat and request.lng:
        found = get_hospital_builtin(lat=request.lat, lng=request.lng)
    else:
        found = search_all_hospitals(keyword=query, limit=10)

    if found:
        response = generate_hospital_response_with_llm(query, found)
    else:
        response = generate_fallback_response(found)

    save_chat_log(request.session_id, query, response, 'hospital_chat')

    return {
        "session_id": request.session_id,
        "response": response,
        "hospitals": found[:5]
    }


@map_router.post("/detail")
async def hospital_detail(request: HospitalDetailRequest):
    found = search_all_hospitals(keyword=request.name, limit=1)

    if found:
        hospital = found[0]
        return {
            "name": hospital["name"],
            "address": hospital["address"],
            "phone": hospital["phone"],
            "level": hospital["level"],
            "departments": hospital["departments"],
            "desc": hospital["desc"],
            "lat": hospital["lat"],
            "lng": hospital["lng"],
            "city": hospital["city"],
            "disclaimer": "以上信息来源于公开数据，仅供参考。不构成对任何医院的推荐或评价。"
        }

    return {
        "name": request.name,
        "detail": "未找到该医院的详细信息",
        "disclaimer": "以上信息来源于公开数据，仅供参考。"
    }


@map_router.get("/ak")
async def get_map_ak():
    """返回百度地图 AK 供前端使用"""
    ak = get_baidu_ak()
    if not ak:
        raise HTTPException(status_code=500, detail="百度地图AK未配置")
    return {"ak": ak}


@map_router.get("/baidu/search")
async def baidu_search(
    query: str = Query(..., description="搜索关键词"),
    region: str = Query("北京", description="城市"),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
):
    """通过百度地图 API 搜索医院"""
    results = baidu_place_search(query, region, lat, lng)
    return {
        "results": results,
        "total": len(results),
        "disclaimer": "以上医院信息来源于百度地图公开数据，仅供参考。",
    }
