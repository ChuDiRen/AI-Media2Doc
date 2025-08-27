# -*- coding: UTF-8 -*-
import os

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
LLM_MODEL_ID = os.getenv("MODEL_ID")
LLM_API_KEY = os.getenv("ARK_API_KEY") or os.getenv("LLM_API_KEY")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 4096))
TOS_ACCESS_KEY = os.getenv("TOS_ACCESS_KEY")
TOS_SECRET_KEY = os.getenv("TOS_SECRET_KEY")
TOS_ENDPOINT = os.getenv("TOS_ENDPOINT")
TOS_REGION = os.getenv("TOS_REGION")
TOS_BUCKET = os.getenv("TOS_BUCKET")
AUC_APP_ID = os.getenv("AUC_APP_ID")
AUC_ACCESS_TOKEN = os.getenv("AUC_ACCESS_TOKEN")
AUC_CLUSTER_ID = os.getenv("AUC_CLUSTER_ID", None)  # 选填, 填这个可以试用
WEB_ACCESS_PASSWORD = os.getenv("WEB_ACCESS_PASSWORD", None)  # 选填, 填这个可以开启 Web 端访问密码

# 小鹅通配置
XIAOE_COOKIE = os.getenv("XIAOE_COOKIE", None)  # 小鹅通Cookie，用于访问已购买课程
XIAOE_APP_ID = os.getenv("XIAOE_APP_ID", None)  # 小鹅通APP ID，可选
XIAOE_HOST = os.getenv("XIAOE_HOST", None)  # 小鹅通API域名，可选
