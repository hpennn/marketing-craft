"""
Skills API Router - 技能API路由，含积分检查
支持 JSON 和 FormData 两种请求格式
"""
import os
import json
import tempfile
import base64
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from typing import Optional, List
from pydantic import BaseModel

from skills.registry import registry
from skills.engine import engine
from credits_database import register_user, get_user_credits, deduct_credits

logger = logging.getLogger(__name__)

router = APIRouter()

# 技能执行消耗积分
CREDIT_COST_SKILL = 20

# 临时文件目录
TEMP_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "uploads")
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)


class ExecuteRequest(BaseModel):
    """技能执行请求（JSON格式）"""
    text: Optional[str] = ""
    format: Optional[str] = None
    platform: Optional[str] = None
    style: Optional[str] = None
    extra: Optional[dict] = None
    user_id: Optional[str] = ""


class TaskCreateRequest(BaseModel):
    """任务创建请求"""
    input: str
    skill_id: Optional[str] = None
    user_id: Optional[str] = ""


@router.get("/skills")
async def list_skills():
    """获取所有可用技能列表"""
    skills = registry.list_all()
    return {
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "icon": s.icon,
                "description": s.description,
                "input_type": s.input_type,
                "output_type": s.output_type,
                "tags": s.tags,
                "enabled": s.enabled,
            }
            for s in skills
        ]
    }


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str):
    """获取单个技能详情"""
    skill = registry.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    return {
        "id": skill.id,
        "name": skill.name,
        "icon": skill.icon,
        "description": skill.description,
        "input_type": skill.input_type,
        "output_type": skill.output_type,
        "tags": skill.tags,
        "enabled": skill.enabled,
    }


def _resolve_user_id(request_user_id: str, fastapi_request: Request) -> str:
    """从请求中解析有效的用户ID"""
    effective_user_id = request_user_id
    if fastapi_request:
        auth_header = fastapi_request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            from auth_database import verify_token
            user_info = verify_token(token)
            if user_info:
                effective_user_id = f"user_{user_info['user_id']}"
    return effective_user_id


def _check_credits(user_id: str):
    """检查积分是否足够"""
    if not user_id:
        return
    register_user(user_id)
    credits = get_user_credits(user_id)
    if credits < CREDIT_COST_SKILL:
        raise HTTPException(
            status_code=402,
            detail={
                "message": "积分不足，请充值后继续使用",
                "required": CREDIT_COST_SKILL,
                "remaining": credits,
            }
        )


async def _save_upload_files(files: List[UploadFile]) -> List[dict]:
    """保存上传的文件到临时目录，返回文件信息列表"""
    import time as _time
    saved_files = []
    for f in files:
        if not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1] or ".bin"
        safe_name = f"upload_{int(_time.time()*1000)}_{id(f)}{ext}"
        filepath = os.path.join(TEMP_UPLOAD_DIR, safe_name)
        
        content = await f.read()
        with open(filepath, "wb") as out:
            out.write(content)
        
        file_info = {
            "filename": f.filename,
            "filepath": filepath,
            "content_type": f.content_type or "application/octet-stream",
            "size": len(content),
            "ext": ext.lower(),
        }
        
        # 如果是图片，生成base64编码
        if ext.lower() in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"):
            file_info["base64"] = base64.b64encode(content).decode("utf-8")
            file_info["data_uri"] = f"data:{f.content_type or 'image/png'};base64,{file_info['base64']}"
        
        saved_files.append(file_info)
        logger.info(f"Saved uploaded file: {f.filename} -> {filepath} ({len(content)} bytes)")
    
    return saved_files


@router.post("/skills/{skill_id}/execute")
async def execute_skill(
    skill_id: str,
    fastapi_request: Request,
):
    """执行指定技能，含积分检查。支持JSON和FormData两种格式"""
    # 读取原始请求判断Content-Type
    content_type = fastapi_request.headers.get("content-type", "")
    
    text = ""
    fmt = None
    platform = None
    style = None
    user_id = ""
    files = None
    saved_files = []
    
    logger.warning(f"[DEBUG] execute_skill: content_type='{content_type}', skill_id={skill_id}")
    if "multipart/form-data" in content_type:
        # FormData格式：读取表单字段和文件
        form = await fastapi_request.form()
        text = form.get("text", "") or ""
        fmt = form.get("format")
        platform = form.get("platform")
        style = form.get("style")
        user_id = form.get("user_id", "") or ""
        
        # 收集文件 - 使用属性检测而非 isinstance，避免类型判断失败
        file_list = []
        for key, value in form.multi_items():
            if key == 'files' and hasattr(value, 'filename') and value.filename and hasattr(value, 'read'):
                logger.warning(f"[DEBUG] Found file: key={key}, filename={value.filename}, type={type(value).__name__}, module={type(value).__module__}")
                file_list.append(value)
        
        logger.warning(f"[DEBUG] form items count: {len(form.multi_items())}, file_list count: {len(file_list)}")
        for _k, _v in form.multi_items():
            logger.warning(f"[DEBUG] form item: key={_k}, type={type(_v).__name__}, value_preview={str(_v)[:100]}")
        if file_list:
            saved_files = await _save_upload_files(file_list)
            logger.warning(f"[DEBUG] saved_files count: {len(saved_files)}")
    else:
        # JSON格式
        try:
            body = await fastapi_request.json()
        except Exception:
            body = {}
        text = body.get("text", "") or ""
        fmt = body.get("format")
        platform = body.get("platform")
        style = body.get("style")
        user_id = body.get("user_id", "") or ""
    
    # 优先使用Token认证
    effective_user_id = _resolve_user_id(user_id, fastapi_request)

    # ===== 积分检查 =====
    _check_credits(effective_user_id)

    # 构建input_data
    input_data = {"text": text}
    if fmt:
        input_data["format"] = fmt
    if platform:
        input_data["platform"] = platform
    if style:
        input_data["style"] = style

    # 处理上传的文件
    if saved_files:
        input_data["files"] = saved_files
        # 便捷字段：第一个图片的base64和路径
        first_image = next((f for f in saved_files if "base64" in f), None)
        if first_image:
            input_data["image_path"] = first_image["filepath"]
            input_data["image_base64"] = first_image["base64"]
            input_data["image_data_uri"] = first_image["data_uri"]

    logger.warning(f"[DEBUG] input_data keys: {list(input_data.keys())}, has_image_data_uri={bool(input_data.get('image_data_uri'))}, has_files={bool(input_data.get('files'))}")
    try:
        result = await engine.execute(skill_id, input_data)
    finally:
        # 清理上传的临时文件
        for f_info in saved_files:
            try:
                fp = f_info.get("filepath", "")
                if fp and os.path.exists(fp):
                    os.unlink(fp)
            except Exception:
                pass

    # ===== 技能执行成功后扣积分 =====
    remaining_credits = -1
    if effective_user_id:
        deduct_credits(effective_user_id, CREDIT_COST_SKILL, f"技能执行: {skill_id}")
        remaining_credits = get_user_credits(effective_user_id)

    result_dict = result.to_dict()
    result_dict["remaining_credits"] = remaining_credits
    return result_dict


@router.post("/tasks")
async def create_task(request: TaskCreateRequest, fastapi_request: Request = None):
    """创建任务（自动匹配技能），含积分检查"""
    effective_user_id = _resolve_user_id(request.user_id, fastapi_request)

    _check_credits(effective_user_id)

    if request.skill_id:
        result = await engine.execute(
            request.skill_id, {"text": request.input}
        )
    else:
        result = await engine.auto_execute(request.input)

    remaining_credits = -1
    if effective_user_id:
        skill_desc = request.skill_id or "自动匹配"
        deduct_credits(effective_user_id, CREDIT_COST_SKILL, f"任务执行: {skill_desc}")
        remaining_credits = get_user_credits(effective_user_id)

    result_dict = result.to_dict()
    result_dict["remaining_credits"] = remaining_credits
    return result_dict


@router.get("/tasks")
async def get_tasks(limit: int = 50):
    """获取任务历史"""
    tasks = engine.get_task_history(limit)
    return {"tasks": tasks, "total": len(tasks)}
