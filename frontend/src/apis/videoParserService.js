/**
 * 视频链接解析服务
 * 支持小鹅通等平台的视频链接解析
 */
import httpService from './http'

/**
 * 解析视频链接
 * @param {string} videoUrl - 视频链接
 * @returns {Promise<Object>} 解析结果
 */
export const parseVideoUrl = async (videoUrl) => {
  try {
    const response = await httpService.post('/api/v3/bots/chat/completions', {
      messages: [{ role: 'user', content: videoUrl }]
    }, {
      headers: {
        'request-action': 'parse_video_url'
      }
    })
    
    if (response.data && response.data.metadata) {
      return {
        success: true,
        data: response.data.metadata
      }
    }
    
    throw new Error('解析响应格式错误')
  } catch (error) {
    console.error('视频链接解析失败:', error)
    return {
      success: false,
      error: error.response?.data?.message || error.message || '解析失败'
    }
  }
}

/**
 * 从URL下载视频
 * @param {string} videoUrl - 视频链接
 * @returns {Promise<Object>} 下载结果
 */
export const downloadVideoFromUrl = async (videoUrl) => {
  try {
    const response = await httpService.post('/api/v3/bots/chat/completions', {
      messages: [{ role: 'user', content: videoUrl }]
    }, {
      headers: {
        'request-action': 'download_video_from_url'
      }
    })
    
    if (response.data && response.data.metadata) {
      return {
        success: true,
        data: response.data.metadata
      }
    }
    
    throw new Error('下载响应格式错误')
  } catch (error) {
    console.error('视频下载失败:', error)
    return {
      success: false,
      error: error.response?.data?.message || error.message || '下载失败'
    }
  }
}

/**
 * 验证视频链接格式
 * @param {string} url - 视频链接
 * @returns {Object} 验证结果
 */
export const validateVideoUrl = (url) => {
  if (!url || typeof url !== 'string') {
    return { valid: false, error: '请输入有效的链接' }
  }
  
  // 基本URL格式验证
  const urlPattern = /^https?:\/\/.+/i
  if (!urlPattern.test(url)) {
    return { valid: false, error: '请输入有效的HTTP/HTTPS链接' }
  }
  
  // 小鹅通链接特征检测
  const xiaoePatterns = [
    /xiaoeknow\.com/i,
    /pri-cdn-tx\.xiaoeknow\.com/i,
    /vod2\.myqcloud\.com.*\.m3u8/i,
    /xiaoe-tech\.com/i
  ]
  
  const isXiaoeUrl = xiaoePatterns.some(pattern => pattern.test(url))
  
  if (!isXiaoeUrl) {
    return { 
      valid: false, 
      error: '暂时只支持小鹅通平台的视频链接' 
    }
  }
  
  return { valid: true, platform: 'xiaoe' }
}

/**
 * 获取支持的平台列表
 * @returns {Array} 支持的平台信息
 */
export const getSupportedPlatforms = () => {
  return [
    {
      name: '小鹅通',
      key: 'xiaoe',
      description: '支持小鹅通平台的视频课程链接',
      examples: [
        'https://xiaoeknow.com/...',
        'https://pri-cdn-tx.xiaoeknow.com/...',
        'https://vod2.myqcloud.com/...m3u8'
      ]
    }
  ]
}

export default {
  parseVideoUrl,
  downloadVideoFromUrl,
  validateVideoUrl,
  getSupportedPlatforms
}
