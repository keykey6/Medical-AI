import requests
import base64
import os
import tempfile
import json

from config import settings


def get_multimodal_model():
    return settings.OLLAMA_MULTIMODAL_MODEL

def analyze_image(image_path_or_base64, prompt="请用中文描述这张图片的内容"):
    try:
        url = "http://localhost:11434/api/generate"
        
        if image_path_or_base64.startswith('data:image/'):
            base64_image = image_path_or_base64.split(',')[1]
        elif os.path.isfile(image_path_or_base64):
            with open(image_path_or_base64, 'rb') as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
        else:
            base64_image = image_path_or_base64
        
        system_prompt = """
你是一个专业的中文图像分析助手。请严格遵守以下规则：

1. **语言要求**: 所有输出必须使用纯中文，禁止任何英文单词、短语或句子。

2. **分析规则**:
   - 仅做客观描述，不进行疾病诊断
   - 不提供任何治疗建议
   - 不推荐任何药物或疗法
   - 保持中立、客观的语气

3. **格式要求**:
   - 使用清晰、简洁的中文描述图片内容
   - 避免专业术语，使用通俗易懂的语言
   - 描述要基于图片中的视觉信息

4. **必须附加免责声明**:
   - 描述完成后必须添加："以上描述为客观观察，不构成任何医疗诊断或治疗建议。如您有健康疑虑，请及时前往正规医院就诊。"
"""
        
        data = {
            "model": get_multimodal_model(),
            "prompt": f"图片分析任务：{prompt}\n\n请用纯中文客观描述图片内容，不进行任何诊断。",
            "system": system_prompt,
            "images": [base64_image],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "max_tokens": 1500
            }
        }
        
        response = requests.post(url, json=data, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            description = result.get("response", "").strip()
            
            if not "以上描述为客观观察" in description:
                description += "\n\n以上描述为客观观察，不构成任何医疗诊断或治疗建议。如您有健康疑虑，请及时前往正规医院就诊。"
            
            if any(char.isascii() and char.isalpha() for char in description):
                clean_description = ''.join([c for c in description if not (c.isascii() and c.isalpha())])
                description = clean_description
            
            return description
        else:
            return f"图像分析失败，状态码: {response.status_code}"
    
    except Exception as e:
        print(f"图像分析异常: {e}")
        return "抱歉，图像分析服务暂时不可用。请稍后重试或联系人工客服。"

async def analyze_image_stream(image_path_or_base64, prompt="请用中文描述这张图片的内容"):
    try:
        url = "http://localhost:11434/api/generate"
        
        if image_path_or_base64.startswith('data:image/'):
            base64_image = image_path_or_base64.split(',')[1]
        elif os.path.isfile(image_path_or_base64):
            with open(image_path_or_base64, 'rb') as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
        else:
            base64_image = image_path_or_base64
        
        system_prompt = """
你是一个专业的中文图像分析助手。请严格遵守以下规则：

1. **语言要求**: 所有输出必须使用纯中文，禁止任何英文单词、短语或句子。

2. **分析规则**:
   - 仅做客观描述，不进行疾病诊断
   - 不提供任何治疗建议
   - 不推荐任何药物或疗法
   - 保持中立、客观的语气

3. **格式要求**:
   - 使用清晰、简洁的中文描述图片内容
   - 避免专业术语，使用通俗易懂的语言
"""
        
        data = {
            "model": get_multimodal_model(),
            "prompt": f"图片分析任务：{prompt}\n\n请用纯中文客观描述图片内容，不进行任何诊断。",
            "system": system_prompt,
            "images": [base64_image],
            "stream": True,
            "options": {
                "temperature": 0.1,
                "max_tokens": 1500
            }
        }
        
        response = requests.post(url, json=data, stream=True, timeout=120)
        
        if response.status_code == 200:
            disclaimer_added = False
            for line in response.iter_lines():
                if line:
                    try:
                        result = json.loads(line)
                        if "response" in result:
                            chunk = result["response"]
                            clean_chunk = ''.join([c for c in chunk if not (c.isascii() and c.isalpha())])
                            yield clean_chunk
                        if result.get("done") and not disclaimer_added:
                            yield "\n\n以上描述为客观观察，不构成任何医疗诊断或治疗建议。如您有健康疑虑，请及时前往正规医院就诊。"
                            disclaimer_added = True
                    except:
                        pass
        else:
            yield "图像分析失败"
    
    except Exception as e:
        print(f"图像分析异常: {e}")
        yield "抱歉，图像分析服务暂时不可用。请稍后重试或联系人工客服。"

def validate_image_format(file_name):
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic']
    ext = os.path.splitext(file_name.lower())[1]
    return ext in valid_extensions

def validate_image_size(file_size_bytes):
    max_size = 15 * 1024 * 1024
    return file_size_bytes <= max_size

def save_temp_image(file_content):
    fd, path = tempfile.mkstemp(suffix='.jpg')
    try:
        os.write(fd, file_content)
        return path
    finally:
        os.close(fd)

def cleanup_temp_image(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"临时图片已清理: {file_path}")
    except Exception as e:
        print(f"清理临时图片失败: {e}")

def check_multimodal_model():
    try:
        url = "http://localhost:11434/api/tags"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            models = response.json()
            model_name = get_multimodal_model()
            model_exists = any(m.get("name") == model_name for m in models.get("models", []))
            return model_exists, f"模型 {model_name} 已就绪" if model_exists else f"模型 {model_name} 未找到"
        return False, "无法连接到Ollama"
    except Exception as e:
        return False, f"检查模型失败: {e}"