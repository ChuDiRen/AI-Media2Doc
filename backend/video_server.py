#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门处理视频链接解析的FastAPI服务器
"""

import os
import sys
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 添加backend目录到Python路径
backend_path = Path(__file__).parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 导入视频解析器
try:
    from actions.video_parser import XiaoETongParser, VideoParserError
    PARSER_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入视频解析器: {e}")
    PARSER_AVAILABLE = False

# 创建FastAPI应用
app = FastAPI(
    title="AI-Media2Doc Video Parser API",
    description="视频链接解析服务",
    version="1.0.0"
)

# 请求模型
class VideoLinkRequest(BaseModel):
    url: str
    options: Optional[Dict[str, Any]] = None

class VideoLinkResponse(BaseModel):
    success: bool
    message: str
    video_info: Optional[Dict[str, Any]] = None
    download_url: Optional[str] = None
    error: Optional[str] = None

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "parser_available": PARSER_AVAILABLE,
        "message": "Video Parser API is running"
    }

# 视频链接解析端点
@app.post("/api/parse-video-link", response_model=VideoLinkResponse)
async def parse_video_link(request: VideoLinkRequest):
    """解析视频链接"""
    
    if not PARSER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="视频解析器不可用，请检查依赖安装"
        )
    
    try:
        print(f"📹 开始解析视频链接: {request.url}")
        
        # 检查是否是小鹅通链接
        if "xiaoe" in request.url.lower() or any(domain in request.url for domain in [
            "hctestedu.com", "xiaoe-tech.com", "xiaoeknow.com"
        ]):
            print("🎯 检测到小鹅通链接，使用专用解析器")
            
            # 使用小鹅通解析器
            parser = XiaoETongParser()
            
            # 解析视频信息
            video_info = await parser.parse_video_info(request.url)
            
            if video_info:
                print(f"✅ 解析成功: {video_info}")
                return VideoLinkResponse(
                    success=True,
                    message="视频链接解析成功",
                    video_info=video_info,
                    download_url=video_info.get("video_url")
                )
            else:
                print("❌ 解析失败：未能获取视频信息")
                return VideoLinkResponse(
                    success=False,
                    message="未能从链接中提取视频信息",
                    error="解析失败"
                )
        else:
            print("⚠️ 不支持的视频平台")
            return VideoLinkResponse(
                success=False,
                message="暂不支持该视频平台",
                error="不支持的平台"
            )
            
    except VideoParserError as e:
        print(f"❌ 视频解析错误: {str(e)}")
        return VideoLinkResponse(
            success=False,
            message=f"视频解析失败: {str(e)}",
            error=str(e)
        )
        
    except Exception as e:
        print(f"❌ 服务器错误: {str(e)}")
        print(f"📋 错误详情: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )

# 获取支持的平台列表
@app.get("/api/supported-platforms")
async def get_supported_platforms():
    """获取支持的视频平台列表"""
    return {
        "platforms": [
            {
                "name": "小鹅通",
                "domains": ["xiaoe-tech.com", "xiaoeknow.com", "hctestedu.com"],
                "description": "支持小鹅通平台的视频课程解析"
            }
        ]
    }

# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "AI-Media2Doc Video Parser API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "parse": "/api/parse-video-link",
            "platforms": "/api/supported-platforms"
        }
    }

if __name__ == "__main__":
    print("🚀 启动 AI-Media2Doc 视频解析服务器")
    print("📡 服务地址: http://localhost:8080")
    print("📋 API文档: http://localhost:8080/docs")
    print("-" * 50)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        reload=False,  # 生产环境建议设为False
        log_level="info"
    )
