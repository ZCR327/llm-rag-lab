# HTTPS 设置说明

## 概述

本项目已配置 HTTPS，使用自签证书（开发用）。生产环境建议用 Let's Encrypt 正式证书。

## 当前状态

- ✅ Nginx SSL termination 已配置（`docker/nginx.conf`）
- ✅ 自签证书已生成（`docker/ssl/localhost.crt` / `localhost.key`）
- ✅ HTTP 自动 301 重定向到 HTTPS
- ✅ TLS 1.2/1.3，HTTP/2 启用
- ✅ HSTS / X-Frame-Options / X-Content-Type-Options 等安全头
- ✅ `remote_client_config.json` 默认走 `https://localhost`

## 启动

```bash
cd "C:\Users\xiaomi\Desktop\智能回收社\积分系统（最终改版)\docker"
docker-compose up -d
```

启动后：
- `http://localhost` → 自动 301 → `https://localhost`
- `https://localhost` → 进入应用
- `https://localhost/health` → 健康检查
- `https://localhost/api/...` → REST API

## 浏览器警告

因为是**自签证书**，浏览器会显示"您的连接不是私密连接"。两种处理方式：

### 选项 1：临时跳过警告
- Chrome/Edge：点击 "高级" → "继续前往 localhost（不安全）"
- Firefox：点击 "高级" → "接受风险并继续"

### 选项 2：信任自签证书（推荐）
把 `docker/ssl/localhost.crt` 导入 Windows 受信任的根证书颁发机构：

1. 双击 `localhost.crt` → "安装证书"
2. 选择"本地计算机"
3. 选择"将所有的证书都放入下列存储" → "受信任的根证书颁发机构"
4. 完成

之后 Chrome / Edge 不会再警告（Firefox 仍需独立信任，见 `about:preferences#privacy` → Certificates → View Certificates → Import）。

## 切换到生产证书（Let's Encrypt）

生产部署建议使用 Let's Encrypt 免费证书。步骤：

1. 替换 `docker/ssl/localhost.crt` 和 `localhost.key` 为正式证书
2. 调整 `docker/nginx.conf` 中：
   - `ssl_certificate` / `ssl_certificate_key` 路径
   - `server_name _` → `server_name yourdomain.com`
   - 删除 80 端口 server block 中的 redirect（或者保留用于 ACME http-01）
3. 启动 certbot 自动续期容器

参考 DEPLOY.md 第 129-148 行的示例。

## 验证

启动后验证 HTTPS 是否生效：

```bash
# 应该看到 301 重定向
curl -I http://localhost

# 应该看到 200 + HTTPS 头
curl -I https://localhost --insecure

# 测试 API
curl -X POST https://localhost/api/login --insecure \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## 客户端配置

`remote_client_config.json`：

```json
{
  "host": "https://localhost",
  "username": "admin",
  "password": "<set-real-password>"
}
```

如果浏览器/客户端要跳过 SSL 验证（仅开发用），可在 `远程连接.py` 里加 `urllib3.disable_warnings()` 和 `context.check_hostname = False`。

## 文件清单

| 文件 | 说明 |
|---|---|
| `docker/nginx.conf` | Nginx 配置（HTTP→HTTPS 重定向 + HTTPS server） |
| `docker/ssl/localhost.crt` | 自签证书（含 SAN: localhost, 127.0.0.1） |
| `docker/ssl/localhost.key` | 证书私钥（2048-bit RSA，5 年有效） |
| `docker/ssl/localhost.pem` | cert + key 合并（备用） |
| `docker/ssl/localhost.pfx` | PKCS#12 格式（含私钥，密码 changeit） |
| `remote_client_config.json` | 默认 host 改为 `https://localhost` |

## 重新生成证书

如果证书过期（5 年）或需要更新：

```powershell
# PowerShell
$cert = New-SelfSignedCertificate -DnsName "localhost", "127.0.0.1" `
  -CertStoreLocation "cert:\CurrentUser\My" `
  -NotAfter (Get-Date).AddYears(5) `
  -KeyAlgorithm RSA -KeyLength 2048

# 导出 PFX
$pfx = "C:\path\to\ssl\localhost.pfx"
$cert | Export-PfxCertificate -FilePath $pfx -Password (ConvertTo-SecureString "changeit" -AsPlainText -Force)

# 用 Python 提取 PEM（用 extract_pem.py 脚本）
python extract_pem.py
```

或者用 openssl（如果已装）：

```bash
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout localhost.key -out localhost.crt \
  -days 1825 -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```
