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
