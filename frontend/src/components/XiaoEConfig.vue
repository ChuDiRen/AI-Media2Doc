<template>
  <div class="xiaoe-config">
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>🎓 小鹅通配置</span>
          <el-button 
            type="primary" 
            size="small" 
            @click="testAuth"
            :loading="testing"
          >
            测试连接
          </el-button>
        </div>
      </template>

      <el-form :model="config" label-width="120px" size="default">
        <el-form-item label="Cookie">
          <el-input
            v-model="config.cookie"
            type="textarea"
            :rows="3"
            placeholder="请输入小鹅通Cookie（登录后在浏览器开发者工具中获取）"
            @blur="saveConfig"
          />
          <div class="help-text">
            <el-text size="small" type="info">
              获取方法：登录小鹅通 → F12开发者工具 → Network → 复制Cookie
            </el-text>
          </div>
        </el-form-item>

        <el-form-item label="APP ID">
          <el-input
            v-model="config.app_id"
            placeholder="可选，从课程链接中提取（如：appisb9y2un7034）"
            @blur="saveConfig"
          />
        </el-form-item>

        <el-form-item label="API域名">
          <el-input
            v-model="config.host"
            placeholder="可选，如：xet.citv.cn 或 h5.xiaoeknow.com"
            @blur="saveConfig"
          />
        </el-form-item>
      </el-form>

      <!-- 认证状态显示 -->
      <div v-if="authStatus" class="auth-status">
        <el-alert
          :title="authStatus.title"
          :type="authStatus.type"
          :description="authStatus.description"
          show-icon
          :closable="false"
        />
        
        <!-- 用户信息显示 -->
        <div v-if="userInfo" class="user-info">
          <el-descriptions title="用户信息" :column="2" size="small">
            <el-descriptions-item label="昵称">{{ userInfo.nickname || '未知' }}</el-descriptions-item>
            <el-descriptions-item label="手机">{{ userInfo.phone || '未绑定' }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>

      <!-- 使用说明 -->
      <el-collapse class="help-collapse">
        <el-collapse-item title="📖 配置说明" name="help">
          <div class="help-content">
            <h4>如何获取Cookie：</h4>
            <ol>
              <li>在浏览器中登录小鹅通课程页面</li>
              <li>按F12打开开发者工具</li>
              <li>切换到Network（网络）标签</li>
              <li>刷新页面，找到任意请求</li>
              <li>在Request Headers中复制Cookie值</li>
            </ol>
            
            <h4>如何获取APP ID：</h4>
            <p>从课程链接中提取，例如：</p>
            <code>https://appisb9y2un7034.xet.citv.cn/...</code>
            <p>其中 <strong>appisb9y2un7034</strong> 就是APP ID</p>
            
            <h4>注意事项：</h4>
            <ul>
              <li>Cookie有时效性，过期后需要重新获取</li>
              <li>仅支持已购买课程的下载</li>
              <li>请遵守小鹅通平台使用条款</li>
            </ul>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import httpService from '../apis/http'

// 响应式数据
const config = reactive({
  cookie: '',
  app_id: '',
  host: ''
})

const testing = ref(false)
const authStatus = ref(null)
const userInfo = ref(null)

// 保存配置到localStorage
const saveConfig = () => {
  try {
    localStorage.setItem('xiaoe_config', JSON.stringify(config))
    console.log('小鹅通配置已保存')
  } catch (error) {
    console.error('保存配置失败:', error)
  }
}

// 从localStorage加载配置
const loadConfig = () => {
  try {
    const saved = localStorage.getItem('xiaoe_config')
    if (saved) {
      const savedConfig = JSON.parse(saved)
      Object.assign(config, savedConfig)
      console.log('小鹅通配置已加载')
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

// 测试认证
const testAuth = async () => {
  if (!config.cookie.trim()) {
    ElMessage.warning('请先配置Cookie')
    return
  }

  testing.value = true
  authStatus.value = null
  userInfo.value = null

  try {
    const response = await httpService.post('/api/v3/bots/chat/completions', {
      messages: [{ 
        role: 'user', 
        content: JSON.stringify({
          cookie: config.cookie,
          app_id: config.app_id,
          host: config.host
        })
      }]
    }, {
      headers: {
        'request-action': 'test_xiaoe_auth'
      }
    })

    if (response.data && response.data.metadata) {
      const result = response.data.metadata
      
      if (result.status === 'success') {
        authStatus.value = {
          title: '认证成功',
          type: 'success',
          description: '小鹅通配置有效，可以正常使用'
        }
        userInfo.value = result.user_info
        ElMessage.success('小鹅通认证成功')
      } else {
        authStatus.value = {
          title: '认证失败',
          type: 'error',
          description: result.config_error || result.auth_result?.message || '认证失败'
        }
        ElMessage.error('小鹅通认证失败')
      }
    }
  } catch (error) {
    console.error('认证测试失败:', error)
    authStatus.value = {
      title: '测试失败',
      type: 'error',
      description: error.response?.data?.message || error.message || '网络请求失败'
    }
    ElMessage.error('认证测试失败')
  } finally {
    testing.value = false
  }
}

// 组件挂载时加载配置
onMounted(() => {
  loadConfig()
})

// 导出配置供其他组件使用
defineExpose({
  config,
  testAuth,
  saveConfig
})
</script>

<style scoped>
.xiaoe-config {
  margin: 20px 0;
}

.config-card {
  max-width: 800px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.help-text {
  margin-top: 5px;
}

.auth-status {
  margin: 20px 0;
}

.user-info {
  margin-top: 15px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 6px;
}

.help-collapse {
  margin-top: 20px;
}

.help-content {
  line-height: 1.6;
}

.help-content h4 {
  color: #409eff;
  margin: 15px 0 10px 0;
}

.help-content ol, .help-content ul {
  margin: 10px 0;
  padding-left: 20px;
}

.help-content code {
  background-color: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}
</style>
