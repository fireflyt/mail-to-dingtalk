# Mail to DingTalk Bot

**腾讯企业邮箱 → 钉钉机器人推送工具**

本工具用于定时检查指定发件人的邮件，并将邮件内容（主题、发件人、收件人、时间、正文）推送到钉钉群机器人，支持 **HTML 转 Markdown**，并提供日志记录功能。

---

## 功能特性

- ✅ 连接 **腾讯企业邮箱 IMAP**，自动检查未读邮件  
- ✅ 仅推送来自指定发件人的邮件（精确匹配邮箱地址）  
- ✅ 自动解析邮件主题、正文（优先 HTML → 转 Markdown）  
- ✅ 支持 **钉钉机器人加签安全设置**  
- ✅ 日志功能（文件 + 控制台），按日期存储  
- ✅ 自动标记已读，避免重复推送  
- ✅ 定时轮询，默认间隔 10 秒  

---
## 使用方法

### 1. 克隆项目
```bash
git clone https://github.com/fireflyt/mail-to-dingtalk.git
cd mail-to-dingtalk
```
### 2. 安装依赖
```bash
pip install requests html2text
```
### 3. 修改配置

* IMAP_HOST = "imap.exmail.qq.com"
* EMAIL_USER = "xxx"        # 企业邮箱账号
* EMAIL_PASS = "xxx"        # 企业邮箱密码（或授权码）
* SENDER_FILTER = "system@notice.aliyun.com"  # 指定发件人
* DING_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
* DING_SECRET = ""  # 如果开启了加签，请填写密钥，否则留空
* CHECK_INTERVAL = 10       # 检查间隔秒数
* LOG_LEVEL = logging.INFO  # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL

### 4. 运行程序
```bash
python mail_to_ding.py
```
* 日志会输出到控制台，并保存在 logs/ 目录下，例如：logs/mail_to_ding_20250910.log
* 日志示例：
- 2025-09-10 10:23:45 - INFO - 启动腾讯企业邮箱 → 钉钉推送服务
- 2025-09-10 10:23:45 - INFO - 监控发件人: system@notice.aliyun.com
- 2025-09-10 10:23:55 - INFO - 找到 1 封未读邮件，开始处理...
- 2025-09-10 10:23:55 - INFO - 推送成功: 阿里云告警通知
- 2025-09-10 10:23:55 - INFO - 邮件处理完成并标记为已读: 阿里云告警通知
  
### 5. 适用场景

监控阿里云、腾讯云等系统通知邮件

将告警邮件推送到钉钉群，实现 运维告警通知

内部消息邮件转发到钉钉
