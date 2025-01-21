import json
import inspect
from openai import OpenAI
from rich import print
from pydantic import TypeAdapter
from pprint import pprint
import requests
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# Implement 3 hàm


def get_current_weather(location: str, unit: str):
    """Get the current weather in a given location"""
    # Hardcoded response for demo purposes
    return "Trời rét vãi nôi, 7 độ C"


def get_stock_price(symbol: str):
    # Không làm gì cả, để hàm trống
    pass


def truncate_text(text: str, max_chars: int = 5000) -> str:
    """Cắt ngắn văn bản để giảm số lượng token"""
    if len(text) <= max_chars:
        return text
    
    # Cắt đến vị trí dấu chấm gần nhất trước max_chars
    truncated = text[:max_chars]
    last_period = truncated.rfind('.')
    if last_period > 0:
        truncated = truncated[:last_period + 1]
    
    return truncated + "\n[Nội dung đã được cắt ngắn...]"


# Bài 2: Implement hàm `view_website`, sử dụng `requests` và JinaAI để đọc markdown từ URL
def view_website(url: str):
    """Đọc nội dung website từ URL được cung cấp và trả về dưới dạng markdown"""
    try:
        urlJina = "https://r.jina.ai/"
        print(f"Đang truy cập URL: {urlJina + url}")

        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        response = requests.get(urlJina + url, headers=headers)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        # Xử lý và làm sạch nội dung
        content = response.text
        content = content.encode('utf-8', errors='ignore').decode('utf-8')
        
        # Cắt ngắn nội dung để giảm số lượng token do groq chỉ đọc được 6000 token
        content = truncate_text(content)
        
        print("Đã lấy được nội dung website thành công")
        return content
        
    except requests.RequestException as e:
        error_msg = f"Lỗi khi truy cập website: {str(e)}"
        print(error_msg)
        return error_msg


# Bài 1: Thay vì tự viết object `tools`, hãy xem lại bài trước, sửa code và dùng `inspect` và `TypeAdapter` để define `tools`
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city name"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit"
                    }
                },
                "required": ["location", "unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get the current stock price of a given symbol",
            "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "view_website",
            "description": inspect.getdoc(view_website),
            "parameters": TypeAdapter(view_website).json_schema()
        }
    }
]

# https://platform.openai.com/api-keys
# client = OpenAI(
#     api_key='sk-proj-XXXX',
# )
# COMPLETION_MODEL = "gpt-4o-mini"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
COMPLETION_MODEL = "llama-3.3-70b-versatile"

messages = [{"role": "user", "content": "https://vnexpress.net/tong-thong-trump-ky-khoang-200-van-kien-sau-khi-nham-chuc-4841389.html"}]

print("Bước 1: Gửi message lên cho LLM")
print(messages)

response = client.chat.completions.create(
    model=COMPLETION_MODEL,
    messages=messages,
    tools=tools
)

print("Bước 2: LLM đọc và phân tích ngữ cảnh LLM")
print(response)

print("Bước 3: Lấy kết quả từ LLM")
tool_call = response.choices[0].message.tool_calls[0]

print(tool_call)
arguments = json.loads(tool_call.function.arguments)

print("Bước 4: Chạy function get_current_weather ở máy mình")

if tool_call.function.name == 'get_current_weather':
    weather_result = get_current_weather(
        arguments.get('location'), arguments.get('unit'))
    # Hoặc code này cũng tương tự
    # weather_result = get_current_weather(**arguments)
    print(f"Kết quả bước 4: {weather_result}")

    print("Bước 5: Gửi kết quả lên cho LLM")
    messages.append(response.choices[0].message)
    messages.append({
        "role": "tool",
        "content": weather_result,
        "tool_call_id": tool_call.id
    })

    pprint(messages)

    final_response = client.chat.completions.create(
        model=COMPLETION_MODEL,
        messages=messages
        # Ở đây không có tools cũng không sao, vì ta không cần gọi nữa
    )
    print(
        f"Kết quả cuối cùng từ LLM: {final_response.choices[0].message.content}.")
elif tool_call.function.name == 'view_website':
    data_result = view_website(arguments.get('url'))
    print("Kết quả bước 4: Đã nhận được nội dung website")

    print("Bước 5: Gửi kết quả lên cho LLM")
    messages.append(response.choices[0].message)
    messages.append({
        "role": "tool",
        "content": data_result if data_result else "Không thể đọc được nội dung website",
        "tool_call_id": tool_call.id
    })

    sys_prompt = f"""Hãy tóm tắt nội dung sau đây một cách ngắn gọn, súc tích. Tập trung vào các điểm chính và thông tin quan trọng nhất.
        Định dạng phản hồi:
        - Tiêu đề chính (nếu có)
        - Tóm tắt ngắn gọn (3-4 câu)
        - Các điểm chính (dạng bullet points)
        
        Nội dung cần tóm tắt:
        {data_result}
        """
    
    messages.append({"role": "user", "content": sys_prompt})

    final_response = client.chat.completions.create(
        model=COMPLETION_MODEL,
        messages=messages
    )
    
    print(f"Kết quả cuối cùng từ LLM: {final_response.choices[0].message.content}.")
