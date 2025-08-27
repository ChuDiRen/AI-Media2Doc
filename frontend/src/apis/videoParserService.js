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
      model: 'video-parser',  // 添加必需的model参数
      messages: [{ role: 'user', content: videoUrl }]
    }, {
      headers: {
        'request-action': 'parse_video_url'
      }
    })
    
    // 添加调试信息
    console.log('API响应:', response)
    console.log('响应数据:', response.data)
    console.log('metadata:', response.data?.metadata)
    console.log('直接metadata:', response.metadata)

    // 检查不同的响应结构
    let metadata = null
    if (response.data && response.data.metadata) {
      metadata = response.data.metadata
    } else if (response.metadata) {
      metadata = response.metadata
    } else if (response.data) {
      // 如果response.data就是我们需要的数据
      metadata = response.data
    }

    if (metadata) {
      return {
        success: true,
        data: metadata
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
      model: 'video-downloader',  // 添加必需的model参数
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
    /xiaoe-tech\.com/i,
    /hctestedu\.com/i,  // 华测教育自定义域名
    /\.xet\.citv\.cn/i,  // 小鹅通标准域名格式
    /app[a-zA-Z0-9]+\.h5\.xiaoeknow\.com/i,  // 小鹅通H5域名
    /detail\/l_[a-zA-Z0-9]+/i  // 小鹅通课程详情页面路径
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
        'https://vod2.myqcloud.com/...m3u8',
        'https://www.hctestedu.com/detail/l_xxx/...',
        'https://appisb9y2un7034.xet.citv.cn/...'
      ]
    }
  ]
}

/**
 * 测试小鹅通认证
 * @param {Object} authConfig - 认证配置 {cookie, app_id, host}
 * @returns {Promise<Object>} 测试结果
 */
export const testXiaoEAuth = async (authConfig) => {
  try {
    const response = await httpService.post('/api/v3/bots/chat/completions', {
      model: 'xiaoe-auth-test',  // 添加必需的model参数
      messages: [{ role: 'user', content: JSON.stringify(authConfig) }]
    }, {
      headers: {
        'request-action': 'test_xiaoe_auth'
      }
    })

    if (response.data && response.data.metadata) {
      return {
        success: true,
        data: response.data.metadata
      }
    }

    throw new Error('测试响应格式错误')
  } catch (error) {
    console.error('小鹅通认证测试失败:', error)
    return {
      success: false,
      error: error.response?.data?.message || error.message || '测试失败'
    }
  }
}

export default {
  parseVideoUrl,
  downloadVideoFromUrl,
  validateVideoUrl,
  getSupportedPlatforms,
  testXiaoEAuth
}
