# 授权与认证 (Authentication)

## 概述

滴答清单使用 OAuth 2.0 协议进行用户授权和访问令牌管理。开发者需要先注册应用获取客户端凭证，然后通过 OAuth 流程获取用户的访问令牌。

## 获取客户端凭证

1. 访问 [滴答清单开发者中心](https://developer.dida365.com/manage)
2. 注册您的应用
3. 获取：
   - **Client ID**：应用程序的唯一标识符
   - **Client Secret**：应用程序的密钥（保密）

## OAuth 2.0 授权流程

### 步骤 1：重定向用户授权

将用户重定向到滴答清单授权页面：

```
https://dida365.com/oauth/authorize?scope=tasks:read%20tasks:write&client_id=YOUR_CLIENT_ID&state=YOUR_STATE&redirect_uri=YOUR_REDIRECT_URI&response_type=code
```

**参数说明：**

| 参数 | 描述 | 是否必需 |
|------|------|----------|
| `client_id` | 应用程序的 Client ID | 是 |
| `scope` | 权限范围，以空格分隔 | 是 |
| `state` | 随机字符串，用于防止 CSRF 攻击 | 是 |
| `redirect_uri` | 用户授权后的回调 URL | 是 |
| `response_type` | 固定为 `code` | 是 |

**权限范围 (scope)：**

- `tasks:read`：读取任务权限
- `tasks:write`：写入任务权限

**示例：**

```python
import secrets
import urllib.parse

def get_authorization_url(client_id: str, redirect_uri: str) -> str:
    """生成授权 URL"""
    state = secrets.token_urlsafe(32)
    scope = "tasks:read tasks:write"

    params = {
        "client_id": client_id,
        "scope": scope,
        "state": state,
        "redirect_uri": redirect_uri,
        "response_type": "code"
    }

    query_string = urllib.parse.urlencode(params)
    return f"https://dida365.com/oauth/authorize?{query_string}"

# 使用示例
auth_url = get_authorization_url(
    client_id="YOUR_CLIENT_ID",
    redirect_uri="https://yourapp.com/callback"
)
print(f"请访问以下 URL 进行授权：{auth_url}")
```

### 步骤 2：接收授权码

用户授权后，滴答清单会将用户重定向回您的 `redirect_uri`，并在查询参数中附带授权码：

```
https://yourapp.com/callback?code=AUTHORIZATION_CODE&state=ORIGINAL_STATE
```

**查询参数：**

- `code`：授权码，用于后续换取访问令牌
- `state`：第一步中传递的 `state` 参数（用于验证）

**处理回调的示例：**

```python
from flask import Flask, request, redirect
from urllib.parse import urlparse

app = Flask(__name__)

@app.route('/callback')
def oauth_callback():
    """处理 OAuth 回调"""
    # 验证 state（防止 CSRF 攻击）
    state = request.args.get('state')
    stored_state = get_stored_state()  # 从会话或存储中获取
    if state != stored_state:
        return "状态验证失败", 400

    # 获取授权码
    code = request.args.get('code')
    if not code:
        return "未收到授权码", 400

    # 使用授权码换取访问令牌
    access_token = exchange_code_for_token(code)

    # 保存访问令牌（示例：保存到数据库）
    save_access_token(access_token)

    return redirect('/success')

def get_stored_state():
    """获取存储的 state 值"""
    # 从会话、缓存或数据库中获取
    return session.get('oauth_state')
```

### 步骤 3：交换访问令牌

向滴答清单令牌端点发送 POST 请求，用授权码换取访问令牌：

```bash
curl -X POST "https://dida365.com/oauth/token" \
  -H "Authorization: Basic $(echo -n 'YOUR_CLIENT_ID:YOUR_CLIENT_SECRET' | base64)" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "code=AUTHORIZATION_CODE&grant_type=authorization_code&redirect_uri=YOUR_REDIRECT_URI"
```

**请求参数：**

| 参数 | 描述 |
|------|------|
| `client_id` | Client ID（通过 Basic Auth 提供） |
| `client_secret` | Client Secret（通过 Basic Auth 提供） |
| `code` | 步骤 2 获取的授权码 |
| `grant_type` | 固定为 `authorization_code` |
| `scope` | 权限范围（与第一步一致） |
| `redirect_uri` | 回调 URL（与第一步一致） |

**Python 实现：**

```python
import base64
import httpx
import urllib.parse

async def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> str:
    """使用授权码换取访问令牌"""
    # 生成 Basic Auth 头
    credentials = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode()

    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://dida365.com/oauth/token",
            headers=headers,
            data=data
        )
        response.raise_for_status()

        token_data = response.json()
        return token_data["access_token"]

# 使用示例
access_token = await exchange_code_for_token(
    code="YOUR_AUTHORIZATION_CODE",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    redirect_uri="YOUR_REDIRECT_URI"
)
print(f"访问令牌：{access_token}")
```

**成功响应：**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "scope": "tasks:read tasks:write"
}
```

## 使用访问令牌

获取到访问令牌后，在调用 API 时需要在请求头中设置：

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**示例：**

```bash
curl -X GET "https://api.dida365.com/open/v1/project" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Python 实现：**

```python
import httpx

async def call_api_with_token(endpoint: str, access_token: str) -> dict:
    """使用访问令牌调用 API"""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.dida365.com{endpoint}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

# 使用示例
projects = await call_api_with_token("/open/v1/project", "YOUR_ACCESS_TOKEN")
print(f"共有 {len(projects)} 个项目")
```

## 令牌管理

### 令牌过期

访问令牌通常有过期时间（`expires_in` 字段）。过期后需要使用刷新令牌获取新的访问令牌。

### 刷新访问令牌

```bash
curl -X POST "https://dida365.com/oauth/token" \
  -H "Authorization: Basic $(echo -n 'YOUR_CLIENT_ID:YOUR_CLIENT_SECRET' | base64)" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "refresh_token=YOUR_REFRESH_TOKEN&grant_type=refresh_token"
```

**Python 实现：**

```python
async def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str
) -> dict:
    """刷新访问令牌"""
    credentials = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode()

    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://dida365.com/oauth/token",
            headers=headers,
            data=data
        )
        response.raise_for_status()
        return response.json()

# 使用示例
new_token_data = await refresh_access_token(
    refresh_token="YOUR_REFRESH_TOKEN",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
)
print(f"新访问令牌：{new_token_data['access_token']}")
```

### 令牌存储

**最佳实践：**

1. **安全存储**：将令牌存储在安全的地方（如加密数据库、安全保险库）
2. **定期刷新**：在令牌过期前主动刷新
3. **最小权限**：只申请必要的权限范围
4. **定期轮换**：定期更换 Client Secret

**示例：令牌管理器**

```python
import json
import time
from datetime import datetime, timedelta
from typing import Optional

class TokenManager:
    """访问令牌管理器"""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = "tokens.json"

    def load_tokens(self) -> Optional[dict]:
        """从文件加载令牌"""
        try:
            with open(self.token_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def save_tokens(self, tokens: dict):
        """保存令牌到文件"""
        with open(self.token_file, 'w') as f:
            json.dump(tokens, f, indent=2)

    def is_token_expired(self, tokens: dict) -> bool:
        """检查令牌是否过期"""
        expires_at = tokens.get('expires_at', 0)
        return time.time() > expires_at

    async def get_valid_access_token(self) -> str:
        """获取有效的访问令牌"""
        tokens = self.load_tokens()

        # 如果没有令牌或已过期，尝试刷新
        if not tokens or self.is_token_expired(tokens):
            if tokens and 'refresh_token' in tokens:
                # 使用刷新令牌
                new_tokens = await self.refresh_tokens(tokens['refresh_token'])
                self.save_tokens(new_tokens)
                return new_tokens['access_token']
            else:
                raise Exception("没有有效的访问令牌，需要重新授权")

        return tokens['access_token']

    async def refresh_tokens(self, refresh_token: str) -> dict:
        """刷新令牌"""
        # 实现刷新逻辑...
        pass

# 使用示例
token_manager = TokenManager("YOUR_CLIENT_ID", "YOUR_CLIENT_SECRET")
access_token = await token_manager.get_valid_access_token()
```

## 完整示例

### 完整的 OAuth 流程

```python
import asyncio
import secrets
import urllib.parse
import base64
import httpx
from datetime import datetime, timedelta

class DidaOAuth:
    """滴答清单 OAuth 2.0 客户端"""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.auth_url = "https://dida365.com/oauth/authorize"
        self.token_url = "https://dida365.com/oauth/token"
        self.api_base = "https://api.dida365.com"

    def get_authorization_url(self) -> tuple[str, str]:
        """生成授权 URL"""
        state = secrets.token_urlsafe(32)
        scope = "tasks:read tasks:write"

        params = {
            "client_id": self.client_id,
            "scope": scope,
            "state": state,
            "redirect_uri": self.redirect_uri,
            "response_type": "code"
        }

        query_string = urllib.parse.urlencode(params)
        auth_url = f"{self.auth_url}?{query_string}"
        return auth_url, state

    async def exchange_code_for_token(self, code: str) -> dict:
        """使用授权码换取访问令牌"""
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                headers=headers,
                data=data
            )
            response.raise_for_status()
            token_data = response.json()

            # 计算过期时间
            expires_at = datetime.now().timestamp() + token_data['expires_in']
            token_data['expires_at'] = expires_at

            return token_data

    async def refresh_token(self, refresh_token: str) -> dict:
        """刷新访问令牌"""
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                headers=headers,
                data=data
            )
            response.raise_for_status()
            token_data = response.json()

            # 计算过期时间
            expires_at = datetime.now().timestamp() + token_data['expires_in']
            token_data['expires_at'] = expires_at

            return token_data

    async def call_api(self, endpoint: str, access_token: str, method: str = "GET", data: dict = None):
        """调用 API"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(
                    f"{self.api_base}{endpoint}",
                    headers=headers
                )
            elif method == "POST":
                response = await client.post(
                    f"{self.api_base}{endpoint}",
                    headers=headers,
                    json=data
                )
            elif method == "DELETE":
                response = await client.delete(
                    f"{self.api_base}{endpoint}",
                    headers=headers
                )

            response.raise_for_status()
            return response.json()

# 使用示例
async def main():
    oauth = DidaOAuth(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        redirect_uri="https://yourapp.com/callback"
    )

    # 步骤 1：生成授权 URL
    auth_url, state = oauth.get_authorization_url()
    print(f"请访问以下 URL 进行授权：")
    print(auth_url)

    # 用户授权后，获取回调 URL 中的 code
    # 这里假设用户已完成授权并返回了 code
    code = input("请输入授权码：")

    # 步骤 2：换取访问令牌
    token_data = await oauth.exchange_code_for_token(code)
    access_token = token_data['access_token']

    print(f"获取访问令牌成功：{access_token[:20]}...")

    # 步骤 3：调用 API
    projects = await oauth.call_api("/open/v1/project", access_token)
    print(f"共有 {len(projects)} 个项目")

# 运行示例
asyncio.run(main())
```

## 安全注意事项

1. **HTTPS**：始终使用 HTTPS 进行授权和数据传输
2. **State 参数**：始终验证 state 参数以防止 CSRF 攻击
3. **Client Secret**：绝对不要在客户端代码中暴露 Client Secret
4. **令牌存储**：安全存储访问令牌和刷新令牌
5. **最小权限**：只申请必要的权限范围
6. **定期刷新**：在令牌过期前及时刷新

## 错误处理

### 常见错误码

| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| `invalid_request` | 请求参数错误 | 检查请求参数是否正确 |
| `invalid_client` | Client ID 或 Secret 错误 | 检查客户端凭证 |
| `invalid_grant` | 授权码无效或已过期 | 重新进行授权流程 |
| `invalid_scope` | 权限范围错误 | 检查 scope 参数 |
| `access_denied` | 用户拒绝授权 | 提示用户重新授权 |
| `unsupported_grant_type` | 不支持的授权类型 | 检查 grant_type 参数 |

### 错误示例

```json
{
  "error": "invalid_grant",
  "error_description": "The authorization code is invalid"
}
```

## 常见问题

**Q: 访问令牌多久过期？**

A: 通常为 1 小时（3600 秒），具体以响应中的 `expires_in` 字段为准。

**Q: 如何撤销访问令牌？**

A: 滴答清单目前不支持主动撤销访问令牌，令牌过期后自动失效。

**Q: 一个用户可以授权多个应用吗？**

A: 是的，用户可以授权多个应用，每个应用有独立的访问令牌。

**Q: 如何处理授权过期？**

A: 使用 refresh_token 获取新的访问令牌，无需用户重新授权。

---

**文档版本**: 1.0
**最后更新**: 2025年11月16日
**相关文档**: [任务](tasks.md) | [项目](projects.md)
