# -*- coding: UTF-8 -*-
"""
视频链接解析模块
支持小鹅通等平台的视频链接解析和下载
"""
import re
import os
import time
import json
import hashlib
import tempfile
from typing import Optional, Dict, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from Cryptodome.Cipher import AES
from arkitect.core.component.llm import ArkChatRequest
from arkitect.core.errors import APIException
from arkitect.types.llm.model import ArkChatResponse
from throttled import Throttled, per_sec, MemoryStore

from .dispatcher import ActionDispatcher

STORE = MemoryStore()

class VideoParserError(Exception):
    """视频解析异常"""
    pass

class XiaoETongParser:
    """小鹅通视频解析器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site'
        }
    
    def is_xiaoe_url(self, url: str) -> bool:
        """检查是否为小鹅通视频链接"""
        xiaoe_patterns = [
            r'xiaoeknow\.com',
            r'pri-cdn-tx\.xiaoeknow\.com',
            r'vod2\.myqcloud\.com.*\.m3u8',
            r'xiaoe-tech\.com',
            r'hctestedu\.com',  # 添加hctestedu.com域名
            r'\.xiaoe\.com',    # 通用小鹅通域名
        ]
        return any(re.search(pattern, url) for pattern in xiaoe_patterns)
    
    def extract_m3u8_url(self, page_url: str) -> str:
        """从页面URL提取M3U8链接"""
        try:
            print(f"🔍 开始提取M3U8链接: {page_url}")

            # 添加更多请求头以绕过反爬虫
            enhanced_headers = {
                **self.headers,
                'Referer': page_url,
                'X-Requested-With': 'XMLHttpRequest'
            }

            response = requests.get(page_url, headers=enhanced_headers, timeout=30)
            response.raise_for_status()

            print(f"📄 页面获取成功，长度: {len(response.text)}")

            # 首先尝试从Nuxt.js的__NUXT__对象中提取数据
            nuxt_match = re.search(r'window\.__NUXT__\s*=\s*(\{.*?\});?\s*$', response.text, re.MULTILINE | re.DOTALL)
            if nuxt_match:
                print("🎯 找到Nuxt.js数据对象")
                try:
                    # 简化的JSON解析，查找视频相关数据
                    nuxt_content = nuxt_match.group(1)

                    # 在Nuxt数据中查找视频URL模式
                    video_patterns = [
                        r'"video_url"\s*:\s*"([^"]*\.m3u8[^"]*)"',
                        r'"play_url"\s*:\s*"([^"]*\.m3u8[^"]*)"',
                        r'"playUrl"\s*:\s*"([^"]*\.m3u8[^"]*)"',
                        r'"hls_url"\s*:\s*"([^"]*\.m3u8[^"]*)"',
                        r'"m3u8_url"\s*:\s*"([^"]*\.m3u8[^"]*)"',
                    ]

                    for pattern in video_patterns:
                        matches = re.findall(pattern, nuxt_content, re.IGNORECASE)
                        if matches:
                            m3u8_url = matches[0].replace('\\/', '/').replace('\/', '/')
                            print(f"✅ 从Nuxt数据中找到视频URL: {m3u8_url}")
                            if self.is_valid_m3u8_url(m3u8_url):
                                return m3u8_url

                except Exception as e:
                    print(f"⚠️ 解析Nuxt数据失败: {str(e)}")

            # 查找M3U8链接的多种模式（增强版）
            m3u8_patterns = [
                r'"play_url":"([^"]*\.m3u8[^"]*)"',
                r'"playUrl":"([^"]*\.m3u8[^"]*)"',
                r'"video_url":"([^"]*\.m3u8[^"]*)"',
                r'"videoUrl":"([^"]*\.m3u8[^"]*)"',
                r'"m3u8_url":"([^"]*\.m3u8[^"]*)"',
                r'"hls_url":"([^"]*\.m3u8[^"]*)"',
                r'https?://[^"\s]*\.m3u8[^"\s]*',
                r'pri-cdn-tx\.xiaoeknow\.com[^"\s]*\.m3u8[^"\s]*',
                r'vod2\.myqcloud\.com[^"\s]*\.m3u8[^"\s]*',
                # 新增小鹅通特定模式
                r'https?://[^"\s]*\.xiaoeknow\.com[^"\s]*\.m3u8[^"\s]*',
                r'https?://[^"\s]*\.xet\.tech[^"\s]*\.m3u8[^"\s]*',
                r'https?://[^"\s]*\.myqcloud\.com[^"\s]*\.m3u8[^"\s]*'
            ]

            print("🔍 使用常规模式搜索M3U8链接...")
            for i, pattern in enumerate(m3u8_patterns):
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    print(f"📹 模式 {i+1} 找到 {len(matches)} 个匹配")
                    for match in matches:
                        m3u8_url = match.replace('\\/', '/').replace('\/', '/')
                        # 确保URL格式正确
                        if not m3u8_url.startswith('http'):
                            if m3u8_url.startswith('//'):
                                m3u8_url = 'https:' + m3u8_url
                            elif m3u8_url.startswith('/'):
                                # 根据当前域名构建完整URL
                                from urllib.parse import urlparse
                                parsed = urlparse(page_url)
                                m3u8_url = f"{parsed.scheme}://{parsed.netloc}" + m3u8_url

                        print(f"🎯 检查URL有效性: {m3u8_url}")
                        if self.is_valid_m3u8_url(m3u8_url):
                            print(f"✅ 找到有效的M3U8链接: {m3u8_url}")
                            return m3u8_url

            # 尝试从JavaScript代码中提取
            print("🔍 尝试从JavaScript代码中提取...")
            js_patterns = [
                r'videoUrl\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'playUrl\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'src\s*[:=]\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'video\s*:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'url\s*:\s*["\']([^"\']*\.m3u8[^"\']*)["\']'
            ]

            for i, pattern in enumerate(js_patterns):
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    print(f"📹 JS模式 {i+1} 找到 {len(matches)} 个匹配")
                    for match in matches:
                        m3u8_url = match.replace('\\/', '/')
                        if not m3u8_url.startswith('http'):
                            if m3u8_url.startswith('//'):
                                m3u8_url = 'https:' + m3u8_url
                        print(f"🎯 检查JS提取的URL: {m3u8_url}")
                        if self.is_valid_m3u8_url(m3u8_url):
                            print(f"✅ 从JS中找到有效链接: {m3u8_url}")
                            return m3u8_url

            # 尝试查找可能的API端点
            print("🔍 尝试查找API端点...")
            api_patterns = [
                r'/api/[^"\s]*video[^"\s]*',
                r'/api/[^"\s]*play[^"\s]*',
                r'/api/[^"\s]*resource[^"\s]*'
            ]

            for pattern in api_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    print(f"🔗 找到可能的API端点: {matches}")
                    # 这里可以进一步请求API端点获取视频信息

            print("❌ 所有模式都未找到有效的M3U8链接")
            raise VideoParserError("未找到有效的M3U8链接")

        except requests.RequestException as e:
            raise VideoParserError(f"获取页面内容失败: {str(e)}")
    
    def is_valid_m3u8_url(self, url: str) -> bool:
        """验证M3U8链接有效性"""
        try:
            response = requests.head(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except:
            return False

    async def parse_video_info(self, page_url: str) -> Optional[Dict]:
        """解析视频信息"""
        try:
            print(f"🎯 开始解析小鹅通视频: {page_url}")

            # 检查是否为小鹅通链接
            if not self.is_xiaoe_url(page_url):
                print("❌ 不是小鹅通链接")
                return None

            # 首先尝试从页面URL中提取资源ID
            resource_id = self._extract_resource_id(page_url)
            if resource_id:
                print(f"📋 提取到资源ID: {resource_id}")

                # 检查资源权限状态
                permission_info = self._check_xiaoe_permissions(page_url, resource_id)
                print(f"🔐 权限检查结果: {permission_info}")

                # 尝试通过API获取视频信息
                api_video_info = await self._get_video_info_from_api(page_url, resource_id)
                if api_video_info:
                    # 合并权限信息
                    api_video_info.update(permission_info)
                    return api_video_info

            # 如果API方法失败，尝试传统的页面解析方法
            try:
                m3u8_url = self.extract_m3u8_url(page_url)
                print(f"📹 找到M3U8链接: {m3u8_url}")

                # 解析M3U8文件
                m3u8_info = self.parse_m3u8(m3u8_url)

                # 构建视频信息
                video_info = {
                    "title": "小鹅通视频课程",
                    "platform": "小鹅通",
                    "video_url": m3u8_url,
                    "format": "m3u8",
                    "segments_count": m3u8_info.get('total_segments', 0),
                    "has_encryption": bool(m3u8_info.get('encryption')),
                    "original_url": page_url
                }

                print(f"✅ 解析成功: {video_info}")
                return video_info

            except VideoParserError as e:
                print(f"❌ 传统解析失败: {str(e)}")

                # 最后尝试：返回基本信息，表示检测到视频但无法获取播放链接
                return {
                    "title": "小鹅通视频课程（需要登录或付费）",
                    "platform": "小鹅通",
                    "video_url": None,
                    "format": "unknown",
                    "segments_count": 0,
                    "has_encryption": False,
                    "original_url": page_url,
                    "status": "需要进一步处理",
                    "message": "检测到小鹅通视频，但可能需要登录或付费才能获取播放链接"
                }

        except Exception as e:
            print(f"❌ 解析异常: {str(e)}")
            return None

    def _extract_resource_id(self, page_url: str) -> Optional[str]:
        """从页面URL中提取资源ID"""
        try:
            # 小鹅通URL格式: https://domain/detail/l_xxxxx/xxx
            match = re.search(r'/detail/(l_[a-zA-Z0-9]+)', page_url)
            if match:
                return match.group(1)
            return None
        except Exception:
            return None

    async def _get_video_info_from_api(self, page_url: str, resource_id: str) -> Optional[Dict]:
        """尝试通过API获取视频信息"""
        try:
            print(f"🔗 尝试通过API获取视频信息: {resource_id}")

            # 从页面URL中提取域名和app_id
            from urllib.parse import urlparse
            parsed = urlparse(page_url)
            domain = parsed.netloc

            # 从日志中发现的真实API端点和参数
            api_endpoints = [
                # 基于日志发现的真实API结构
                f"https://{domain}/xe.course.business.course_detail.get/1.0.0",
                f"https://{domain}/api/xe.course.business.course_detail.get/1.0.0",
                f"https://{domain}/xe.course.business.course.get/1.0.0",
                # 小鹅通的标准API端点
                f"https://appi1q1b9a05586.h5.xiaoeknow.com/xe.course.business.course_detail.get/1.0.0",
                f"https://appi1q1b9a05586.xet.citv.cn/xe.course.business.course_detail.get/1.0.0"
            ]

            # 从URL中提取更多信息
            app_id = "appi1Q1B9A05586"  # 从日志中发现的app_id

            for api_url in api_endpoints:
                try:
                    print(f"🔍 尝试API端点: {api_url}")

                    # 基于日志中发现的参数结构
                    api_data = {
                        "resource_id": resource_id,
                        "resource_type": 6,  # 从日志中看到是专栏类型
                        "app_id": app_id
                    }

                    # 增强的请求头，模拟真实浏览器
                    api_headers = {
                        **self.headers,
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Referer': page_url,
                        'Origin': f"https://{domain}"
                    }

                    response = requests.post(
                        api_url,
                        json=api_data,
                        headers=api_headers,
                        timeout=15
                    )

                    print(f"📊 API响应状态: {response.status_code}")

                    if response.status_code == 200:
                        try:
                            result = response.json()
                            print(f"📊 API响应内容: {result}")

                            # 解析API响应中的视频信息
                            if 'data' in result and result['data']:
                                data = result['data']

                                # 提取视频相关信息
                                video_info = {
                                    "title": data.get('title', '小鹅通课程'),
                                    "platform": "小鹅通",
                                    "video_url": self._extract_video_url_from_data(data),
                                    "format": "api_extracted",
                                    "duration": data.get('duration', 0),
                                    "original_url": page_url,
                                    "resource_id": resource_id,
                                    "resource_type": data.get('resource_type', 6),
                                    "is_free": data.get('is_free', 0),
                                    "have_password": data.get('have_password', 0)
                                }

                                if video_info["video_url"]:
                                    print(f"✅ API成功获取视频信息: {video_info}")
                                    return video_info
                                else:
                                    print("⚠️ API响应中未找到视频URL")

                        except json.JSONDecodeError as e:
                            print(f"⚠️ API响应JSON解析失败: {str(e)}")
                            print(f"📄 响应内容: {response.text[:500]}")

                            # 检查是否是JSONP格式
                            if 'jsonp_' in response.text or 'callback(' in response.text:
                                print("🔍 检测到JSONP格式，尝试提取JSON数据")
                                # 提取JSONP中的JSON数据
                                jsonp_match = re.search(r'jsonp_\w+\((.*)\)', response.text)
                                if jsonp_match:
                                    try:
                                        json_data = json.loads(jsonp_match.group(1))
                                        print(f"📊 JSONP解析成功: {json_data}")

                                        if 'data' in json_data and json_data['data']:
                                            data = json_data['data']
                                            video_info = {
                                                "title": data.get('title', '小鹅通课程'),
                                                "platform": "小鹅通",
                                                "video_url": self._extract_video_url_from_data(data),
                                                "format": "jsonp_extracted",
                                                "duration": data.get('duration', 0),
                                                "original_url": page_url,
                                                "resource_id": resource_id,
                                                "resource_type": data.get('resource_type', 6),
                                                "is_free": data.get('is_free', 0),
                                                "have_password": data.get('have_password', 0)
                                            }

                                            if video_info["video_url"]:
                                                print(f"✅ JSONP成功获取视频信息: {video_info}")
                                                return video_info

                                    except json.JSONDecodeError:
                                        print("❌ JSONP内容也无法解析为JSON")

                    else:
                        print(f"⚠️ API响应状态异常: {response.status_code}")
                        print(f"📄 响应内容: {response.text[:200]}")

                except Exception as e:
                    print(f"⚠️ API端点 {api_url} 失败: {str(e)}")
                    continue

            return None

        except Exception as e:
            print(f"❌ API获取失败: {str(e)}")
            return None

    def _extract_video_url_from_data(self, data: Dict) -> Optional[str]:
        """从API数据中提取视频URL"""
        # 尝试多种可能的视频URL字段
        video_url_fields = [
            'video_url', 'play_url', 'playUrl', 'hls_url',
            'm3u8_url', 'stream_url', 'media_url'
        ]

        for field in video_url_fields:
            if field in data and data[field]:
                return data[field]

        # 检查嵌套结构
        if 'media' in data and isinstance(data['media'], dict):
            for field in video_url_fields:
                if field in data['media'] and data['media'][field]:
                    return data['media'][field]

        return None

    def _check_xiaoe_permissions(self, page_url: str, resource_id: str) -> Dict:
        """检查小鹅通资源的权限状态"""
        try:
            print(f"🔐 检查资源权限: {resource_id}")

            from urllib.parse import urlparse
            parsed = urlparse(page_url)
            domain = parsed.netloc

            # 基于日志中发现的权限检查API
            permission_url = f"https://{domain}/xe.course.business.course_detail.get/1.0.0"

            permission_data = {
                "resource_id": resource_id.replace('l_', 'p_'),  # 转换资源ID格式
                "resource_type": 6  # 专栏类型
            }

            response = requests.post(
                permission_url,
                json=permission_data,
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if 'data' in result:
                    data = result['data']
                    return {
                        "has_permission": data.get('permission', 0) == 1,
                        "is_free": data.get('is_free', 0) == 1,
                        "is_public": data.get('is_public', 0) == 1,
                        "have_password": data.get('have_password', 0) == 1,
                        "is_stop_sell": data.get('is_stop_sell', 0) == 1,
                        "title": data.get('title', ''),
                        "jump_url": data.get('jump_url', '')
                    }

            return {"has_permission": False, "error": "无法获取权限信息"}

        except Exception as e:
            print(f"❌ 权限检查失败: {str(e)}")
            return {"has_permission": False, "error": str(e)}
    
    def parse_m3u8(self, m3u8_url: str) -> Dict:
        """解析M3U8文件"""
        try:
            response = requests.get(m3u8_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            content = response.text
            
            if "#EXTM3U" not in content:
                raise VideoParserError("不是有效的M3U8文件")
            
            # 解析加密信息
            encryption_info = self._parse_encryption(content, m3u8_url)
            
            # 解析TS片段
            ts_segments = self._parse_ts_segments(content, m3u8_url)
            
            return {
                'encryption': encryption_info,
                'segments': ts_segments,
                'total_segments': len(ts_segments)
            }
            
        except requests.RequestException as e:
            raise VideoParserError(f"获取M3U8文件失败: {str(e)}")
    
    def _parse_encryption(self, content: str, base_url: str) -> Optional[Dict]:
        """解析加密信息"""
        if "EXT-X-KEY" not in content:
            return None
        
        key_line = re.search(r'#EXT-X-KEY:(.*)', content)
        if not key_line:
            return None
        
        key_info = key_line.group(1)
        
        # 提取URI
        uri_match = re.search(r'URI="([^"]*)"', key_info)
        if not uri_match:
            return None
        
        key_uri = uri_match.group(1)
        if not key_uri.startswith('http'):
            key_uri = urljoin(base_url, key_uri)
        
        # 提取IV
        iv_match = re.search(r'IV=0x([0-9A-Fa-f]+)', key_info)
        iv = iv_match.group(1) if iv_match else '00000000000000000000000000000000'
        
        return {
            'method': 'AES-128',
            'key_uri': key_uri,
            'iv': iv
        }
    
    def _parse_ts_segments(self, content: str, base_url: str) -> List[str]:
        """解析TS片段列表"""
        base_url = base_url.rsplit('/', 1)[0] + '/'
        
        # 匹配EXTINF和对应的TS文件
        pattern = r'#EXTINF:[^,]*,\s*([^\s#]+)'
        matches = re.findall(pattern, content)
        
        segments = []
        for match in matches:
            if match.startswith('http'):
                segments.append(match)
            else:
                segments.append(urljoin(base_url, match))
        
        return segments
    
    def get_decryption_key(self, key_uri: str) -> bytes:
        """获取解密密钥"""
        try:
            response = requests.get(key_uri, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            raise VideoParserError(f"获取解密密钥失败: {str(e)}")
    
    def download_and_decrypt_segment(self, segment_url: str, key: bytes, iv: str, segment_index: int = 0) -> bytes:
        """下载并解密单个TS片段"""
        try:
            # 添加更多请求头
            segment_headers = {
                **self.headers,
                'Range': 'bytes=0-',  # 支持断点续传
                'Referer': segment_url.split('/')[0] + '//' + segment_url.split('/')[2] + '/'
            }

            # 下载片段，增加重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.get(segment_url, headers=segment_headers, timeout=60)
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(1)  # 重试前等待1秒

            # 解密
            if key:
                # 处理IV：如果没有指定IV，使用片段索引作为IV
                if iv and len(iv) == 32:
                    iv_bytes = bytes.fromhex(iv)
                else:
                    # 使用片段索引作为IV（小鹅通常见做法）
                    iv_bytes = segment_index.to_bytes(16, byteorder='big')

                cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
                decrypted_data = cipher.decrypt(response.content)

                # 移除PKCS7填充
                padding_length = decrypted_data[-1]
                if padding_length <= 16:
                    decrypted_data = decrypted_data[:-padding_length]

                return decrypted_data
            else:
                return response.content

        except requests.RequestException as e:
            raise VideoParserError(f"下载片段失败: {str(e)}")
    
    def download_video(self, m3u8_url: str, output_path: str = None) -> str:
        """下载完整视频"""
        if not output_path:
            output_path = os.path.join(tempfile.gettempdir(), f"xiaoe_video_{int(time.time())}.mp4")
        
        # 解析M3U8
        m3u8_info = self.parse_m3u8(m3u8_url)
        
        # 获取解密密钥
        key = None
        if m3u8_info['encryption']:
            key = self.get_decryption_key(m3u8_info['encryption']['key_uri'])
        
        # 下载并合并所有片段
        total_segments = len(m3u8_info['segments'])
        successful_downloads = 0

        with open(output_path, 'wb') as f:
            for i, segment_url in enumerate(m3u8_info['segments']):
                try:
                    if m3u8_info['encryption']:
                        iv = m3u8_info['encryption']['iv']
                        segment_data = self.download_and_decrypt_segment(segment_url, key, iv, i)
                    else:
                        response = requests.get(segment_url, headers=self.headers, timeout=60)
                        response.raise_for_status()
                        segment_data = response.content

                    f.write(segment_data)
                    successful_downloads += 1
                    print(f"已下载片段 {i+1}/{total_segments} (成功: {successful_downloads})")

                    # 每下载10个片段休息一下，避免被限流
                    if (i + 1) % 10 == 0:
                        time.sleep(0.5)

                except Exception as e:
                    print(f"片段 {i+1} 下载失败: {str(e)}")
                    # 如果失败的片段太多，抛出异常
                    if (i + 1 - successful_downloads) > total_segments * 0.1:  # 失败率超过10%
                        raise VideoParserError(f"下载失败片段过多，已失败 {i + 1 - successful_downloads} 个")
                    continue

        # 检查下载完整性
        if successful_downloads < total_segments * 0.8:  # 成功率低于80%
            raise VideoParserError(f"视频下载不完整，仅成功下载 {successful_downloads}/{total_segments} 个片段")
        
        return output_path

# API接口实现
@ActionDispatcher.register("parse_video_url")
async def parse_video_url(request: ArkChatRequest):
    """解析视频链接"""
    video_url = request.messages[0].content
    
    try:
        parser = XiaoETongParser()
        
        # 检查是否为支持的链接
        if not parser.is_xiaoe_url(video_url):
            raise APIException(
                message="不支持的视频链接格式",
                code="400",
                http_code=400
            )
        
        # 提取M3U8链接
        if video_url.endswith('.m3u8'):
            m3u8_url = video_url
        else:
            m3u8_url = parser.extract_m3u8_url(video_url)
        
        # 解析M3U8信息
        m3u8_info = parser.parse_m3u8(m3u8_url)
        
        yield ArkChatResponse(
            id="parse_video_url",
            choices=[],
            created=int(time.time()),
            model="",
            object="chat.completion",
            usage=None,
            bot_usage=None,
            metadata={
                "m3u8_url": m3u8_url,
                "total_segments": m3u8_info['total_segments'],
                "has_encryption": m3u8_info['encryption'] is not None,
                "status": "success"
            }
        )
        
    except VideoParserError as e:
        raise APIException(
            message=f"视频解析失败: {str(e)}",
            code="500",
            http_code=500
        )
    except Exception as e:
        raise APIException(
            message=f"解析过程中发生错误: {str(e)}",
            code="500",
            http_code=500
        )

@ActionDispatcher.register("download_video_from_url")
async def download_video_from_url(request: ArkChatRequest):
    """从URL下载视频"""
    video_url = request.messages[0].content
    
    try:
        parser = XiaoETongParser()
        
        # 限流控制
        with Throttled(key="video_download", store=STORE, quota=per_sec(limit=2, burst=5)):
            # 提取M3U8链接
            if video_url.endswith('.m3u8'):
                m3u8_url = video_url
            else:
                m3u8_url = parser.extract_m3u8_url(video_url)
            
            # 下载视频
            output_path = parser.download_video(m3u8_url)
            
            # 生成文件名用于上传
            file_hash = hashlib.md5(video_url.encode()).hexdigest()[:8]
            filename = f"xiaoe_video_{file_hash}.mp4"
            
            yield ArkChatResponse(
                id="download_video_from_url",
                choices=[],
                created=int(time.time()),
                model="",
                object="chat.completion",
                usage=None,
                bot_usage=None,
                metadata={
                    "local_path": output_path,
                    "filename": filename,
                    "status": "success"
                }
            )
            
    except VideoParserError as e:
        raise APIException(
            message=f"视频下载失败: {str(e)}",
            code="500",
            http_code=500
        )
    except Exception as e:
        raise APIException(
            message=f"下载过程中发生错误: {str(e)}",
            code="500",
            http_code=500
        )
