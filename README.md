# 可部署Flask应用

这是一个可部署的Flask应用示例，展示了如何使用GitHub Actions进行持续集成和部署。

## 项目结构

- `app/main.py` - Flask应用主文件
- `requirements.txt` - Python依赖
- `Dockerfile` - Docker容器配置
- `Procfile` - 云平台部署配置
- `.github/workflows/` - GitHub Actions工作流
- `tests/` - 单元测试

## 本地运行

1. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

2. 运行应用：
   ```
   python app/main.py
   ```

3. 访问应用：
   - 主页: http://localhost:5000
   - API状态: http://localhost:5000/api/status
   - 健康检查: http://localhost:5000/health
   - 就绪检查: http://localhost:5000/ready
   - 访问者历史: http://localhost:5000/visitors

## 部署选项

### Docker部署
```
docker build -t flask-app .
docker run -p 5000:5000 flask-app
```

### 云平台部署
应用已配置为可在以下平台部署：
- Heroku (通过Procfile)
- AWS Elastic Beanstalk
- Google Cloud Platform
- Microsoft Azure
- Render

## CI/CD

GitHub Actions将：
- 测试代码质量
- 运行单元测试
- 部署到生产环境（仅main分支）
https://github.com/coolshell2000/github-actions-test

## API端点

- `GET /` - 主页
- `GET /api/status` - API状态
- `GET /health` - 健康检查
- `GET /ready` - 就绪检查
- `GET /visitors` - 访问者历史记录
- `GET /login` - 社交登录页面
- `GET /login/google` - Google登录
- `GET /login/wechat` - 微信登录
- `GET /profile` - 用户资料（需登录）
- `GET /logout` - 退出登录

## 社交登录功能

本项目已集成社交登录功能，支持：

- **Google OAuth登录**：用户可通过Google账户登录
- **微信OAuth登录**：用户可通过微信扫码登录
- **统一用户管理**：支持多种登录方式的用户账户统一管理

### 配置社交登录

1. 在 `.env` 文件中配置以下环境变量：
   ```
   SECRET_KEY=your-secret-key-here
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   WECHAT_CLIENT_ID=your-wechat-client-id  # 可选
   WECHAT_CLIENT_SECRET=your-wechat-client-secret  # 可选
   ```

2. 本项目已预配置了Google OAuth密钥，可直接使用

### 在Render上部署时配置环境变量

当在Render上部署此应用时，您需要：

1. 在Render控制台的服务设置中，转到"Environment"标签页
2. 添加以下环境变量：
   - `SECRET_KEY`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `WECHAT_CLIENT_ID`（可选）
   - `WECHAT_CLIENT_SECRET`（可选）

注意：不要将包含敏感信息的 `.env` 文件推送到GitHub仓库，因为这会导致安全问题。Render会在部署过程中使用您在控制台配置的环境变量。

### 启动应用

使用以下命令启动应用：

```
./start.sh
```

## 测试

运行单元测试：
```
python -m pytest tests/ -v
```

## Render 部署

要部署到 Render 平台，请按照以下步骤操作：
1. 在 Render 上创建一个新的 Web Service
2. 连接到您的 GitHub 仓库
3. Render 会自动检测到 Procfile 并使用它来部署应用
4. 部署完成后，Render 会提供一个唯一的 URL，格式为 `https://your-app-name.onrender.com`

部署的应用将可通过 Render 提供的 URL 访问。

https://github-actions-test-u5cx.onrender.com/
