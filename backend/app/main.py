from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import socket
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Prompt Studio API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=2000)
    context: str = Field(default="", max_length=5000)
    audience: str = Field(default="", max_length=1000)
    style: str = Field(default="balanced", pattern="^(balanced|detailed|concise|creative)$")
    include_variables: bool = True
    provider: str = Field(default="custom", max_length=40)
    base_url: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    api_key: str | None = Field(default=None, max_length=1000)


class ModelConfig(BaseModel):
    provider: str = Field(default="custom", max_length=40)
    base_url: str = Field(min_length=8, max_length=500)
    model: str = Field(min_length=1, max_length=200)
    api_key: str = Field(min_length=1, max_length=1000)


PROVIDERS = [
    {"id": "openai", "name": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    {"id": "deepseek", "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    {"id": "qwen", "name": "阿里云百炼 · 通义千问", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    {"id": "siliconflow", "name": "硅基流动", "base_url": "https://api.siliconflow.cn/v1", "model": "Qwen/Qwen3-8B"},
    {"id": "moonshot", "name": "Moonshot · Kimi", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
    {"id": "zhipu", "name": "智谱 BigModel", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
    {"id": "openrouter", "name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "model": "openai/gpt-4o-mini"},
    {"id": "custom", "name": "自定义 OpenAI 兼容接口", "base_url": "", "model": ""},
]


def resolve_model_config(request: GenerateRequest | ModelConfig) -> tuple[str, str, str] | None:
    api_key = getattr(request, "api_key", None) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = getattr(request, "base_url", None) or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = getattr(request, "model", None) or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return api_key, base_url.rstrip("/"), model


def validate_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("接口地址必须是安全的 HTTPS URL，且不能包含账号或密码。")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError("无法解析该接口地址，请检查 URL。") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("为保护本地服务，自定义接口不能指向本机或内网地址。")
    return base_url.rstrip("/")


def event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def demo_prompt(request: GenerateRequest) -> str:
    audience = request.audience.strip() or "需要完成该任务的目标用户"
    context = request.context.strip() or "未提供额外背景；如有关键假设，请先明确说明。"
    variable_note = (
        "将可能变化的信息写成 {{变量名}}，并在末尾列出变量说明。"
        if request.include_variables
        else "使用具体、完整的表述，不保留模板占位变量。"
    )
    detail = {
        "balanced": "内容完整而简洁，避免重复说明。",
        "detailed": "充分拆解任务步骤、判断标准与边界条件。",
        "concise": "优先给出直接可执行的结果，删去不必要的解释。",
        "creative": "在满足目标的前提下提供有辨识度的表达与新颖方案。",
    }[request.style]
    return f"""# 角色
你是一位擅长将目标转化为高质量成果的专业助手。请结合任务需要调用相关领域知识，并以清晰、可靠、可执行为标准。

# 任务
{request.topic.strip()}

# 背景与约束
{context}

# 目标对象
请面向：{audience}。根据对方的知识水平、关注点和使用场景调整内容。

# 执行要求
1. 先识别任务的核心目标和成功标准，再开始作答。
2. 按照适合该任务的步骤完成工作；信息不足时，先说明合理假设，不要编造事实。
3. 提供具体、有用且可以直接采用的内容，并检查前后是否一致。
4. {detail}
5. {variable_note}

# 输出格式
先给出可直接使用的结果，再补充必要的说明。使用清晰的小标题和列表；若任务需要特定格式，严格遵循该格式。

# 完成前检查
- 是否回应了任务的核心目标？
- 是否考虑了目标对象和背景限制？
- 是否存在含糊、重复或未经支持的说法？
- 输出是否便于直接复制和使用？"""


async def demo_chunks(request: GenerateRequest) -> AsyncIterator[str]:
    prompt = demo_prompt(request)
    for start in range(0, len(prompt), 18):
        yield event({"type": "chunk", "content": prompt[start : start + 18]})
        await asyncio.sleep(0.012)


async def model_chunks(request: GenerateRequest, config: tuple[str, str, str]) -> AsyncIterator[str]:
    api_key, base_url, model = config
    base_url = validate_base_url(base_url)
    style_hint = {
        "balanced": "清晰均衡",
        "detailed": "细节充分",
        "concise": "简洁直接",
        "creative": "创意发散",
    }[request.style]
    variable_hint = "保留 {{变量名}} 占位符，并列出变量说明。" if request.include_variables else "不使用占位变量。"
    messages = [
        {
            "role": "system",
            "content": (
                "你是专业的提示词设计师。将用户的简短需求转化为可直接复制使用的高质量中文提示词。"
                "提示词需要包含角色、目标、背景/输入、执行要求、输出格式和质量检查；按任务裁剪，避免空泛套话。"
                f"风格：{style_hint}。{variable_hint}只输出最终提示词，不要解释你的设计过程。"
            ),
        },
        {
            "role": "user",
            "content": f"任务：{request.topic}\n背景：{request.context or '未补充'}\n目标对象：{request.audience or '根据任务合理判断'}",
        },
    ]
    async with httpx.AsyncClient(timeout=httpx.Timeout(90, connect=15)) as client:
        async with client.stream(
            "POST",
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": 0.7, "stream": True},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                payload = json.loads(line[6:])
                content = payload["choices"][0].get("delta", {}).get("content")
                if content:
                    yield event({"type": "chunk", "content": content})


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "api" if os.getenv("OPENAI_API_KEY") else "demo"}


@app.get("/api/providers")
async def providers() -> dict[str, list[dict[str, str]]]:
    return {"providers": PROVIDERS}


@app.post("/api/models/test")
async def test_model(config: ModelConfig) -> dict[str, str | bool]:
    try:
        _, base_url, model = resolve_model_config(config) or ("", config.base_url, config.model)
        base_url = validate_base_url(base_url)
        async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10)) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {config.api_key}"},
                json={"model": model, "messages": [{"role": "user", "content": "Reply with OK."}], "max_tokens": 8},
            )
            response.raise_for_status()
            payload = response.json()
        if not payload.get("choices"):
            raise ValueError("接口已响应，但返回格式不是 OpenAI Chat Completions 格式。")
        return {"ok": True, "provider": config.provider, "model": model, "message": "连接成功，模型已返回响应。"}
    except ValueError as exc:
        return {"ok": False, "provider": config.provider, "model": config.model, "message": str(exc)}
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        message = "API Key 无效或权限不足。" if status in (401, 403) else f"模型服务返回 HTTP {status}，请检查模型名称和接口配置。"
        return {"ok": False, "provider": config.provider, "model": config.model, "message": message}
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        return {"ok": False, "provider": config.provider, "model": config.model, "message": f"连接失败，请检查网络、接口地址和模型服务状态。({type(exc).__name__})"}


@app.post("/api/generate/stream")
async def generate_stream(request: GenerateRequest) -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        config = resolve_model_config(request)
        use_api = config is not None
        yield event({"type": "meta", "mode": "api" if use_api else "demo"})
        try:
            chunks = model_chunks(request, config) if config else demo_chunks(request)
            async for chunk in chunks:
                yield chunk
        except ValueError as exc:
            yield event({"type": "error", "message": str(exc)})
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            detail = str(exc)[:240] or "模型服务暂时不可用"
            yield event({"type": "error", "message": f"AI 服务调用失败：{detail}"})
        yield event({"type": "done"})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
