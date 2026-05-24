import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health_check():
    print("测试1: 健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        print("[PASS] 健康检查通过")
    except Exception as e:
        print(f"[FAIL] 健康检查失败: {e}")

def test_medical_consultation():
    print("\n测试2: 医疗咨询类问题...")
    try:
        data = {"session_id": "test_session", "message": "高血压的常见症状有哪些？"}
        response = requests.post(f"{BASE_URL}/api/chat/send", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "高血压" in result["response"]
        assert result["question_type"] == "医疗咨询"
        print("[PASS] 医疗咨询测试通过")
        print(f"  问题类型: {result['question_type']}")
        print(f"  情绪类型: {result['emotion_type']}")
    except Exception as e:
        print(f"[FAIL] 医疗咨询测试失败: {e}")

def test_registration():
    print("\n测试3: 预约挂号类问题...")
    try:
        data = {"session_id": "test_session", "message": "怎么预约挂号？"}
        response = requests.post(f"{BASE_URL}/api/chat/send", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "挂号" in result["response"] or "预约" in result["response"]
        print("[PASS] 预约挂号测试通过")
        print(f"  问题类型: {result['question_type']}")
    except Exception as e:
        print(f"[FAIL] 预约挂号测试失败: {e}")

def test_medical_fee():
    print("\n测试4: 费用查询类问题...")
    try:
        data = {"session_id": "test_session", "message": "看病要花多少钱？"}
        response = requests.post(f"{BASE_URL}/api/chat/send", json=data)
        assert response.status_code == 200
        result = response.json()
        print("[PASS] 费用查询测试通过")
        print(f"  问题类型: {result['question_type']}")
    except Exception as e:
        print(f"[FAIL] 费用查询测试失败: {e}")

def test_medical_insurance():
    print("\n测试5: 医保政策类问题...")
    try:
        data = {"session_id": "test_session", "message": "医保怎么报销？"}
        response = requests.post(f"{BASE_URL}/api/chat/send", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "医保" in result["response"] or "报销" in result["response"]
        print("[PASS] 医保政策测试通过")
        print(f"  问题类型: {result['question_type']}")
    except Exception as e:
        print(f"[FAIL] 医保政策测试失败: {e}")

def test_department():
    print("\n测试6: 科室介绍类问题...")
    try:
        data = {"session_id": "test_session", "message": "内科是看什么病的？"}
        response = requests.post(f"{BASE_URL}/api/chat/send", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "内科" in result["response"]
        print("[PASS] 科室介绍测试通过")
        print(f"  问题类型: {result['question_type']}")
    except Exception as e:
        print(f"[FAIL] 科室介绍测试失败: {e}")

def test_emotion_anxiety():
    print("\n测试7: 情绪分析-焦虑...")
    try:
        data = {"session_id": "test_session", "message": "我很担心我的病情，不知道该怎么办？"}
        response = requests.post(f"{BASE_URL}/api/chat/send", json=data)
        assert response.status_code == 200
        result = response.json()
        print("[PASS] 情绪分析测试通过")
        print(f"  情绪类型: {result['emotion_type']}")
        print(f"  问题类型: {result['question_type']}")
    except Exception as e:
        print(f"[FAIL] 情绪分析测试失败: {e}")

def test_compliance_block():
    print("\n测试8: 合规拦截-疾病诊断...")
    try:
        data = {"session_id": "test_session", "message": "我得了什么病？帮我诊断一下"}
        response = requests.post(f"{BASE_URL}/api/chat/send", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["is_transfer"] == True
        assert "无法提供疾病诊断" in result["response"]
        print("[PASS] 合规拦截测试通过")
    except Exception as e:
        print(f"[FAIL] 合规拦截测试失败: {e}")

def test_compliance_prescription():
    print("\n测试9: 合规拦截-开处方...")
    try:
        data = {"session_id": "test_session", "message": "帮我开个处方"}
        response = requests.post(f"{BASE_URL}/api/chat/send", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["is_transfer"] == True
        print("[PASS] 开处方拦截测试通过")
    except Exception as e:
        print(f"[FAIL] 开处方拦截测试失败: {e}")

def test_transfer_to_human():
    print("\n测试10: 转人工功能...")
    try:
        response = requests.post(f"{BASE_URL}/api/chat/transfer/test_session")
        assert response.status_code == 200
        result = response.json()
        assert "转接人工客服" in result["message"]
        print("[PASS] 转人工测试通过")
    except Exception as e:
        print(f"[FAIL] 转人工测试失败: {e}")

def test_history():
    print("\n测试11: 历史记录查询...")
    try:
        response = requests.get(f"{BASE_URL}/api/chat/history/test_session")
        assert response.status_code == 200
        result = response.json()
        assert "history" in result
        print("[PASS] 历史记录查询测试通过")
        print(f"  历史记录条数: {len(result['history'])}")
    except Exception as e:
        print(f"[FAIL] 历史记录查询测试失败: {e}")

def test_triage():
    print("\n测试12: 智能分诊...")
    try:
        data = {"session_id": "test_session", "message": "我头痛发烧，应该挂什么科？"}
        response = requests.post(f"{BASE_URL}/api/chat/send", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "科室" in result["response"] or "就诊" in result["response"]
        print("[PASS] 智能分诊测试通过")
    except Exception as e:
        print(f"[FAIL] 智能分诊测试失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("医疗AI智能客服 - 功能测试")
    print("=" * 60)
    
    time.sleep(2)
    
    test_health_check()
    test_medical_consultation()
    test_registration()
    test_medical_fee()
    test_medical_insurance()
    test_department()
    test_emotion_anxiety()
    test_compliance_block()
    test_compliance_prescription()
    test_transfer_to_human()
    test_history()
    test_triage()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)