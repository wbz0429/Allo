**文本请求代码示例**

```Plain Text
import json
import requests

# API 基础地址
Baseurl = "https://api.gptoai.top"

# 你的 API 密钥，需替换成实际的密钥
Skey = "sk-xxxx这里输入你的令牌"

# 请求数据
payload = json.dumps({
    "model": "模型名字",  # 这里替换为实际模型名称，例如 "gemini-1.5-pro"
    "messages": [
        {
            "role": "system",  # 这个是系统提示，可以理解为聊天机器人的设定
            "content": "You are a helpful assistant."  # 这个是机器人的行为设定
        },
        {
            "role": "user",  # 这个是用户的角色
            "content": "hello"  # 这个是用户发送的消息
        }
    ]
})

# 请求 URL
url = Baseurl + "/v1/chat/completions"

# 请求头信息
headers = {
    'Accept': 'application/json',
    'Authorization': f'Bearer {Skey}',  # 使用 f-string 插入密钥
    'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',  # 用户代理信息
    'Content-Type': 'application/json'  # 请求内容类型为 JSON
}

# 发送 POST 请求
response = requests.post(url, headers=headers, data=payload)

# 打印响应内容
print(response.text)


```




**图片请求代码示例**

```Plain Text
import requests
import base64

# 定义中转站的地址和API秘钥
url = "https://api.gptoai.top/v1/chat/completions"
api_key = "你的秘钥"

# 图片的URL
image_url = "https://github.com/dianping/cat/raw/master/cat-home/src/main/webapp/images/logo/cat_logo03.png"

# 下载图片
response = requests.get(image_url)

# 确保请求成功
if response.status_code == 200:
    img_data = response.content
    # 将图片转换为 base64 格式
    img_base64 = base64.b64encode(img_data).decode("utf-8")
    
    # 构造请求体（OpenAI API 格式）- 修改为正确的多模态格式
    data = {
        "model": "gpt-4o",你的模型名称
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请分析这张图片"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                ]
            }
        ]
    }

    # 请求头
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 发送 POST 请求
    response = requests.post(url, json=data, headers=headers)

    # 检查请求是否成功
    if response.status_code == 200:
        print("请求成功，返回结果：")
        print(response.json())
    else:
        print("请求失败，状态码：", response.status_code)
        print("错误信息：", response.text)
else:
    print("图片下载失败，状态码：", response.status_code)

```






## Gemini模型生图调用代码示例

```Plain Text
import requests
import base64
import os
import time
import json # 引入json库，方便打印格式化的json

# --- 1. 配置您的API信息 ---
# 您的中转站点的API Key
API_KEY = "sk-**************************"  # 务必替换成您自己的API Key

# 您的中转站点地址
BASE_URL = "https://api.gptoai.top"

# --- 2. 构造请求 ---
# 完整的请求URL，使用您指定的原生Gemini端口
model_name = "gemini-2.5-flash-image"
url = f"{BASE_URL}/v1beta/models/{model_name}:generateContent"

# 请求头
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# 请求体 (Payload)，采用Gemini原生格式
payload = {
    "contents": [
        {
            "role": "user",
            "parts": [
                {
                    "text": "一只可爱的狐狸，穿着侦探服，拿着放大镜，在夜晚的森林里寻找线索，赛博朋克风格"
                }
            ]
        }
    ],
    # 可以添加生成参数，但这取决于中转站是否支持并透传这些参数
    # "generationConfig": {
    #     "candidateCount": 1,
    #     # 其他可能的参数...
    # },
    # "safetySettings": [
    #     # 安全设置...
    # ]
}

# --- 3. 发送请求并处理响应 ---
try:
    print("🚀 正在向API发送请求 (使用Gemini原生格式)，请稍候...")
    response = requests.post(url, headers=headers, json=payload, timeout=120) # 设置较长的超时时间

    # 检查响应状态码
    response.raise_for_status()

    print("✅ 请求成功，正在解析返回的图片数据...")
    json_response = response.json()

    # --- 4. 从Gemini原生格式的响应中提取、解码并保存图片 ---
    # 预测的响应结构: response -> candidates -> content -> parts -> inlineData
    
    image_found = False
    # 使用 .get() 方法安全地访问可能不存在的键
    candidates = json_response.get('candidates', [])
    
    if not candidates:
        print("❌ 错误：API响应中未找到 'candidates' 字段。")
        print("👇 服务器原始响应:")
        print(json.dumps(json_response, indent=2, ensure_ascii=False))

    for i, candidate in enumerate(candidates):
        parts = candidate.get('content', {}).get('parts', [])
        for part in parts:
            # 检查part中是否包含图片数据
            inline_data = part.get('inlineData')
            if inline_data and 'data' in inline_data:
                image_found = True
                
                # 获取base64编码的图片数据
                b64_data = inline_data['data']
                
                # 解码
                image_bytes = base64.b64decode(b64_data)
                
                # 生成文件名并保存
                timestamp = int(time.time())
                filename = f"gemini_native_image_{timestamp}_{i+1}.png"
                
                with open(filename, "wb") as f:
                    f.write(image_bytes)
                
                print(f"🖼️ 图片已成功保存为: {os.path.abspath(filename)}")
                break # 找到一张图就处理下一张
    
    if not image_found and candidates:
        print("❌ 未在响应中找到图片数据('inlineData')。请检查API返回的结构。")
        print("👇 服务器原始响应:")
        # 使用json库美化输出，方便查看
        print(json.dumps(json_response, indent=2, ensure_ascii=False))


except requests.exceptions.HTTPError as http_err:
    print(f"❌ HTTP 请求失败: {http_err}")
    print(f"服务器返回内容: {response.text}")
except requests.exceptions.RequestException as req_err:
    print(f"❌ 请求发生错误: {req_err}")
except (KeyError, IndexError, TypeError) as e:
    print(f"❌ 解析返回的JSON时出错，格式可能与预期不符: {e}")
    # 打印原始响应以供调试
    print("👇 服务器原始响应:")
    print(response.text)
except Exception as e:
    print(f"❌ 发生未知错误: {e}")
```






## **Gemini支持文本图片上传生图**

```Plain Text
import requests
import base64
import os
import time
import json
import mimetypes # 引入mimetypes库，用于自动判断图片类型

# --- 1. 配置您的API信息 ---
# 您的中转站点的API Key
API_KEY = "sk-**************************"  # 务必替换成您自己的API Key

# 您的中转站点地址
BASE_URL = "https://api.gptoai.top"

# --- 2. 配置输入信息 (新增部分) ---
# 🌟 请在这里指定您要上传的参考图片路径 🌟
INPUT_IMAGE_PATH = "参考图片.jpg"  # 确保这个文件在你的代码目录下，或者写绝对路径

# 🌟 您的文本提示词 🌟
# 告诉模型如何根据你上传的图片进行创作
TEXT_PROMPT = "根据我上传的图片，保持角色的外观特征和动作，将背景完全替换为一个充满霓虹灯和飞行车辆的赛博朋克城市街道，时间是雨夜。"

# 模型名称
model_name = "gemini-2.5-flash-image"
url = f"{BASE_URL}/v1beta/models/{model_name}:generateContent"


# --- 辅助函数：读取本地图片并转为Base64编码 (新增函数) ---
def encode_image_file(image_path):
    """
    读取本地图片文件，将其转换为Base64字符串，并自动检测MIME类型。
    返回符合Gemini API要求的 inlineData 字典结构。
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"找不到指定的输入图片文件: {image_path}")
    
    # 自动猜测图片的 MIME 类型 (例如 image/jpeg, image/png)
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None or not mime_type.startswith('image'):
        # 如果猜不到或者不是图片，默认给一个常用的，但最好确保输入是jpg或png
        print(f"⚠️ 警告: 无法自动识别文件类型或文件不是已知图片格式: {image_path}。默认使用 image/jpeg。")
        mime_type = "image/jpeg"

    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    return {
        "mimeType": mime_type,
        "data": encoded_string
    }

# --- 3. 构造请求 ---

# 请求头
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

print(f"🚀 正在准备发送请求...")

# 尝试读取并编码输入图片
try:
    print(f"📂 正在读取输入图片: {INPUT_IMAGE_PATH}")
    image_data_part = {"inlineData": encode_image_file(INPUT_IMAGE_PATH)}
    print("✅ 输入图片读取并编码成功。")
except FileNotFoundError as e:
    print(f"❌ 错误: {e}")
    exit() # 如果找不到输入图片，直接退出程序
except Exception as e:
    print(f"❌ 处理输入图片时发生未知错误: {e}")
    exit()


# 请求体 (Payload)，采用Gemini原生格式 (已修改为多模态)
# 关键点：在 parts 列表中同时放入图片部分和文本部分
payload = {
    "contents": [
        {
            "role": "user",
            "parts": [
                # Part 1: 上传的图片数据 (建议放在文本前面)
                image_data_part,
                # Part 2: 文本提示词
                {
                    "text": TEXT_PROMPT
                }
            ]
        }
    ],
     "generationConfig": {
        # 某些模型生成图片时，可能需要设置较大的 token 数，或者不需要设置。
        # 如果生成失败，可以尝试注释掉下面这行，或者调整数值。
        # "maxOutputTokens": 8192, 
        "temperature": 0.7 # 控制创造性
     }
}

# --- 4. 发送请求并处理响应 (保持原样) ---
try:
    print(f"📡 正在向API ({model_name}) 发送多模态请求，请稍候...")
    # 这里的 timeout 设置得更大一些，因为上传图片和生成图片都需要时间
    response = requests.post(url, headers=headers, json=payload, timeout=180)

    # 检查响应状态码
    response.raise_for_status()

    print("✅ 请求成功，正在解析返回的数据...")
    json_response = response.json()

    # --- 5. 从Gemini原生格式的响应中提取、解码并保存图片 ---
    # 预测的响应结构: response -> candidates -> content -> parts -> inlineData
    
    image_found = False
    # 使用 .get() 方法安全地访问可能不存在的键
    candidates = json_response.get('candidates', [])
    
    if not candidates:
        print("❌ 错误：API响应中未找到 'candidates' 字段。可能因安全设置被拦截或模型无法处理。")
        print("👇 服务器原始响应:")
        print(json.dumps(json_response, indent=2, ensure_ascii=False))

    for i, candidate in enumerate(candidates):
        # 检查是否因为安全原因结束
        finish_reason = candidate.get('finishReason')
        if finish_reason and finish_reason != 'STOP':
             print(f"⚠️ 警告: 生成因故中止，原因: {finish_reason}")
             # 经常会遇到 SAFETY 类型的停止，需要检查 safetySettings

        parts = candidate.get('content', {}).get('parts', [])
        for part in parts:
            # 检查part中是否包含图片数据
            inline_data = part.get('inlineData')
            if inline_data and 'data' in inline_data:
                image_found = True
                
                # 获取base64编码的图片数据
                b64_data = inline_data['data']
                
                # 解码
                image_bytes = base64.b64decode(b64_data)
                
                # 生成文件名并保存
                timestamp = int(time.time())
                # 区分输入和输出文件
                output_filename = f"gemini_generated_{timestamp}_{i+1}.png"
                
                with open(output_filename, "wb") as f:
                    f.write(image_bytes)
                
                print(f"🎉 图片已成功生成并保存为: {os.path.abspath(output_filename)}")
                break # 找到一张图就处理下一张
    
    if not image_found and candidates:
        print("❌ 未在响应中找到图片数据('inlineData')。请检查API返回的结构。")
        # 有时候模型没生成图片，但返回了文本拒绝理由
        text_response = candidates[0].get('content', {}).get('parts', [{}])[0].get('text')
        if text_response:
             print(f"👇 模型返回的文本信息: \n{text_response}")
        else:
             print("👇 服务器原始响应:")
             print(json.dumps(json_response, indent=2, ensure_ascii=False))


except requests.exceptions.HTTPError as http_err:
    print(f"❌ HTTP 请求失败: {http_err}")
    print(f"服务器返回内容: {response.text}")
except requests.exceptions.RequestException as req_err:
    print(f"❌ 请求发生错误: {req_err}")
except (KeyError, IndexError, TypeError) as e:
    print(f"❌ 解析返回的JSON时出错，格式可能与预期不符: {e}")
    print("👇 服务器原始响应:")
    print(response.text)
except Exception as e:
    print(f"❌ 发生未知错误: {e}")
```




## **Gemini视频分析脚本示例**

```Plain Text
import openai
from openai import OpenAI

# 1. 初始化客户端
client = OpenAI(
    api_key="", #这里填写令牌
    base_url="https://api.gptoai.top/v1"
)

def analyze_video(video_url):
    print(f"--- 正在调用中转站分析视频 ---")
    try:
        response = client.chat.completions.create(
            # 确认你的中转站是否支持 2.5 这种超前版本号，通常是 gemini-2.0-flash
            model="gemini-2.5-flash-lite", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "请详细分析这个视频的内容。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": video_url 
                            }
                        }
                    ],
                }
            ],
            stream=True
        )

        print("AI 响应：")
        for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
                
    except Exception as e:
        print(f"\n错误详情: {e}")

if __name__ == "__main__":
    # 修正点 2: 具体的 URL 放在这里。
    # 修正点 3: 注意 URL 里的空格。如果直接写空格可能会报错，建议像下面这样用引号包裹完整。
    target_url = "https://pub-5717e870c60f429f95d6edbb11a6eb6d.r2.dev/11/CherryStudio%202025-02-08%2013-47-17.mp4"
    #填写你的视频公网url
    analyze_video(target_url)
```


## **Sora视频调用示例**

```Plain Text
import requests
import json
import time

# --- 1. 配置你的 API 信息 ---

FULL_URL = "https://api.gptoai.top/v1/video/generations"

# 你的 API Key
# 请务必替换为你自己的 Key，不要泄露
API_KEY = "sk-*************************" # ！！！ 替换成你的 API Key ！！！

# --- 2. 定义你要生成的视频内容 ---

# 视频生成的模型名称
MODEL_NAME = "sora-2"

# 视频的描述文本 (Prompt)
PROMPT = "一个穿着时尚的女人走在东京的街道上，街道上充满了温暖的霓虹灯和动画城市标牌。她戴着黑色皮夹克、长裙和红色靴子，拎着一个黑色钱包。她戴着太阳镜，涂着红色口红。她走路自信而随意。街道潮湿反光，形成了一个彩色的镜像效果。许多行人走来走去。"

# --- 3. 构建并发送 API 请求 ---

# 请求头，包含认证信息
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


# 注意：未来可能还会有其他参数，如 "n" (数量), "size" (尺寸如 "1080p") 等
payload = {
    "model": MODEL_NAME,
    "prompt": PROMPT,
    # "n": 1, # 如果支持，可以指定生成视频的数量
    # "size": "1080p" # 如果支持，可以指定视频分辨率
}

print(f"正在向 {FULL_URL} 发送请求...")
print(f"使用的模型: {MODEL_NAME}")
print(f"Prompt: {PROMPT[:50]}...") # 只打印部分 prompt

try:
    # 发送 POST 请求
    response = requests.post(FULL_URL, headers=headers, json=payload, timeout=300) # 设置较长的超时时间

    # 检查 HTTP 状态码，如果不是 2xx，则会抛出异常
    response.raise_for_status()

    # 解析返回的 JSON 数据
    result = response.json()

    # --- 4. 处理并打印结果 ---
    print("\n✅ API 响应成功!")
    # 使用 json.dumps 美化输出
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 通常，视频生成是一个异步任务。API 可能不会立即返回视频 URL。
    # 场景1：直接返回数据（包含视频URL）
    # (这是一种可能的返回格式，具体请参考你的中转站文档)
    if 'data' in result and len(result['data']) > 0:
        video_url = result['data'][0].get('url')
        if video_url:
            print(f"\n🎬 视频已生成！URL: {video_url}")
        else:
            print("\n⚠️ 未在响应中找到视频 URL。")

    # 场景2：返回任务ID，需要轮询查询结果
    # (这也是一种常见的处理方式)
    elif 'task_id' in result or 'id' in result:
        task_id = result.get('task_id') or result.get('id')
        status = result.get('status', '未知')
        print(f"\n⏳ 视频生成任务已提交，状态: {status}，任务 ID: {task_id}")
        print("\n脚本将开始自动查询任务状态，请稍候...")

        # --- 5. 自动轮询查询任务状态 ---
        status_url = f"{FULL_URL}/{task_id}"
        max_retries = 30  # 最多查询30次
        wait_time = 20    # 每次查询间隔20秒

        for i in range(max_retries):
            print(f"\n第 {i+1}/{max_retries} 次查询...")
            try:
                status_response = requests.get(status_url, headers=headers, timeout=60)
                status_response.raise_for_status()
                status_result = status_response.json()

                current_status = status_result.get("status")
                video_url = status_result.get("url")

                print(f"当前状态: {current_status}")

                if current_status == "finished" and video_url:
                    print(f"\n🎉 视频已生成！URL: {video_url}")
                    break  # 成功获取URL，退出循环
                elif current_status in ["failed", "error"]:
                    print("\n❌ 视频生成失败。")
                    break

                if i < max_retries - 1:
                    time.sleep(wait_time) # 等待一段时间再查询

            except requests.exceptions.RequestException as poll_err:
                print(f"查询时发生错误: {poll_err}")
        else:
            print("\n⌛️ 查询超时，视频可能仍在处理中。请稍后手动查询。")


except requests.exceptions.HTTPError as http_err:
    print(f"\n❌ HTTP 错误: {http_err}")
    print(f"响应内容: {response.text}")
except requests.exceptions.RequestException as req_err:
    print(f"\n❌ 请求错误: {req_err}")
except Exception as e:
    print(f"\n❌ 发生未知错误: {e}")

```


