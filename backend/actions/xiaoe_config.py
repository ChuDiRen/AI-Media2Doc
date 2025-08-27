# -*- coding: UTF-8 -*-
"""
小鹅通配置管理模块
处理小鹅通认证、配置验证等功能
"""
import re
import json
import requests
from typing import Optional, Dict, Tuple
from urllib.parse import urlparse

import env


class XiaoEConfig:
    """小鹅通配置管理器"""
    
    def __init__(self, cookie: Optional[str] = None, app_id: Optional[str] = None, host: Optional[str] = None):
        """
        初始化小鹅通配置
        
        Args:
            cookie: 小鹅通Cookie
            app_id: 小鹅通APP ID
            host: 小鹅通API域名
        """
        self.cookie = cookie or env.XIAOE_COOKIE
        self.app_id = app_id or env.XIAOE_APP_ID
        self.host = host or env.XIAOE_HOST
        
        # 基础请求头
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site'
        }
    
    def get_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """
        获取带认证的请求头
        
        Args:
            referer: 引用页面URL
            
        Returns:
            包含认证信息的请求头
        """
        headers = self.base_headers.copy()
        
        if self.cookie:
            headers['Cookie'] = self.cookie
        
        if referer:
            headers['Referer'] = referer
            parsed = urlparse(referer)
            headers['Origin'] = f"{parsed.scheme}://{parsed.netloc}"
        
        return headers
    
    def extract_info_from_url(self, url: str) -> Dict[str, Optional[str]]:
        """
        从URL中提取小鹅通相关信息
        
        Args:
            url: 小鹅通课程链接
            
        Returns:
            包含app_id、product_id、host等信息的字典
        """
        info = {
            'app_id': None,
            'product_id': None,
            'host': None,
            'resource_id': None
        }
        
        try:
            parsed = urlparse(url)
            info['host'] = parsed.netloc
            
            # 提取APP ID
            # 格式：https://appisb9y2un7034.xet.citv.cn/...
            app_id_match = re.search(r'app([a-zA-Z0-9]+)\.', parsed.netloc)
            if app_id_match:
                info['app_id'] = f"app{app_id_match.group(1)}"
            
            # 提取产品ID
            # 格式1：/p/course/column/p_608baa19e4b071a81eb6ebbc
            product_match = re.search(r'/p/course/[^/]+/(p_[a-zA-Z0-9]+)', url)
            if product_match:
                info['product_id'] = product_match.group(1)

            # 格式2：从URL参数中提取 from=p_xxxxx
            from urllib.parse import parse_qs
            query_params = parse_qs(parsed.query)
            if 'from' in query_params:
                from_value = query_params['from'][0]
                if from_value.startswith('p_'):
                    info['product_id'] = from_value

            # 提取资源ID
            # 格式1：/detail/l_xxxxx/xxx
            resource_match = re.search(r'/detail/(l_[a-zA-Z0-9]+)', url)
            if resource_match:
                info['resource_id'] = resource_match.group(1)

            # 格式2：/p/t_pc/live_pc/pc/l_xxxxx
            live_match = re.search(r'/p/t_pc/live_pc/pc/(l_[a-zA-Z0-9]+)', url)
            if live_match:
                info['resource_id'] = live_match.group(1)

            # 对于自定义域名，尝试从域名中提取APP ID
            # 如：www.hctestedu.com -> hctestedu
            if not info['app_id'] and not app_id_match:
                domain_parts = parsed.netloc.split('.')
                if len(domain_parts) >= 2:
                    # 取主域名部分作为可能的APP ID
                    potential_app_id = domain_parts[-2]  # 如 hctestedu.com 中的 hctestedu
                    if len(potential_app_id) > 3:  # 确保不是太短的域名
                        info['app_id'] = potential_app_id
            
            print(f"🔍 从URL提取信息: {info}")
            
        except Exception as e:
            print(f"❌ URL信息提取失败: {str(e)}")
        
        return info
    
    def validate_config(self) -> Tuple[bool, str]:
        """
        验证配置是否有效
        
        Returns:
            (是否有效, 错误信息)
        """
        if not self.cookie:
            return False, "未配置小鹅通Cookie"
        
        # 验证Cookie格式
        if not self._is_valid_cookie_format(self.cookie):
            return False, "Cookie格式无效"
        
        return True, "配置有效"
    
    def _is_valid_cookie_format(self, cookie: str) -> bool:
        """验证Cookie格式是否正确"""
        # 基本格式检查：应该包含键值对
        return '=' in cookie and len(cookie) > 10
    
    def test_authentication(self, test_url: Optional[str] = None) -> Dict[str, any]:
        """
        测试认证是否有效
        
        Args:
            test_url: 测试用的课程URL
            
        Returns:
            测试结果
        """
        try:
            # 如果没有提供测试URL，使用默认的API端点测试
            if not test_url:
                test_url = "https://h5.xiaoeknow.com/xe.course.business.course_list.get/1.0.0"
            
            headers = self.get_headers()
            
            # 发送测试请求
            response = requests.get(test_url, headers=headers, timeout=10)
            
            result = {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'authenticated': False,
                'message': ''
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # 检查是否需要登录
                    if 'code' in data:
                        if data['code'] == 0:
                            result['authenticated'] = True
                            result['message'] = '认证成功'
                        elif data['code'] == 401 or data['code'] == 403:
                            result['message'] = '认证失败，请检查Cookie是否有效'
                        else:
                            result['message'] = f"API返回错误码: {data['code']}"
                    else:
                        result['authenticated'] = True
                        result['message'] = '认证成功'
                except json.JSONDecodeError:
                    result['message'] = '响应格式错误'
            else:
                result['message'] = f'HTTP错误: {response.status_code}'
            
            return result
            
        except requests.RequestException as e:
            return {
                'success': False,
                'status_code': 0,
                'authenticated': False,
                'message': f'网络请求失败: {str(e)}'
            }
    
    def get_user_info(self) -> Optional[Dict]:
        """
        获取用户信息（如果Cookie有效）
        
        Returns:
            用户信息字典或None
        """
        try:
            # 尝试获取用户信息的API端点
            api_url = "https://h5.xiaoeknow.com/xe.user.center.user_info.get/1.0.0"
            
            headers = self.get_headers()
            response = requests.post(api_url, headers=headers, json={}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0 and 'data' in data:
                    return data['data']
            
            return None
            
        except Exception as e:
            print(f"❌ 获取用户信息失败: {str(e)}")
            return None


def get_xiaoe_config(cookie: Optional[str] = None, app_id: Optional[str] = None, host: Optional[str] = None) -> XiaoEConfig:
    """
    获取小鹅通配置实例
    
    Args:
        cookie: 可选的Cookie覆盖
        app_id: 可选的APP ID覆盖
        host: 可选的域名覆盖
        
    Returns:
        XiaoEConfig实例
    """
    return XiaoEConfig(cookie=cookie, app_id=app_id, host=host)
