import os
import subprocess
import tempfile
import json

def speech_to_text(audio_data, format="wav"):
    try:
        with tempfile.NamedTemporaryFile(suffix=f'.{format}', delete=False) as f:
            f.write(audio_data)
            temp_path = f.name
        
        try:
            result = subprocess.run(
                ['whisper', temp_path, '--model', 'small', '--language', 'Chinese', '--output_format', 'json'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                output_file = temp_path.replace(f'.{format}', '.json')
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    text = data.get('text', '').strip()
                    os.remove(output_file)
                    return text if text else "未能识别语音内容"
                else:
                    return "未能识别语音内容"
            else:
                return f"语音识别失败: {result.stderr[:100]}"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except subprocess.TimeoutExpired:
        return "语音识别超时"
    except FileNotFoundError:
        return "未找到Whisper，请先安装：pip install openai-whisper"
    except Exception as e:
        return f"语音识别异常: {str(e)[:100]}"

def is_whisper_available():
    try:
        result = subprocess.run(['whisper', '--help'], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False