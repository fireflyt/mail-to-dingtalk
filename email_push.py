#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯企业邮箱 → 钉钉机器人推送
作者: Kubecc
版本: v1.2 (添加日志记录功能)
"""
import imaplib
import email
import requests
import time
import hmac
import hashlib
import base64
import urllib.parse
import os
import logging
from datetime import datetime
import html2text

# ---------------- 配置区域 ----------------
IMAP_HOST = "imap.exmail.qq.com"
EMAIL_USER = "xxx"   # 企业邮箱账号
EMAIL_PASS = "xxx"            # 企业邮箱密码（或授权码）
SENDER_FILTER = "system@notice.aliyun.com"  # 指定发件人

DING_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
DING_SECRET = ""  # 如果钉钉机器人开启了加签安全设置，请填写密钥，否则留空

CHECK_INTERVAL = 10  # 检查间隔秒数
LOG_LEVEL = logging.INFO  # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
# ------------------------------------------

# 设置日志记录
def setup_logger():
    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建日志文件名（按日期）
    log_file = os.path.join(log_dir, f"mail_to_ding_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 创建日志记录器
    logger = logging.getLogger("MailToDing")
    logger.setLevel(LOG_LEVEL)
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(LOG_LEVEL)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # 添加处理器到记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 初始化日志记录器
logger = setup_logger()

def get_ding_signature():
    """生成钉钉加签 URL"""
    if not DING_SECRET:
        return DING_WEBHOOK
    timestamp = str(round(time.time() * 1000))
    secret_enc = DING_SECRET.encode('utf-8')
    string_to_sign = f"{timestamp}\n{DING_SECRET}"
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return f"{DING_WEBHOOK}&timestamp={timestamp}&sign={sign}"

def send_to_ding_markdown(title, md_content):
    """发送 Markdown 消息到钉钉"""
    url = get_ding_signature()
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": md_content
        }
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            logger.error(f"钉钉推送失败: {r.status_code} - {r.text}")
        else:
            result = r.json()
            if result.get("errcode") == 0:
                logger.info(f"推送成功: {title}")
            else:
                logger.error(f"推送失败: {title} - {result.get('errmsg')}")
    except Exception as e:
        logger.error(f"钉钉请求异常: {e}")

def extract_email_content(msg):
    """优先取 HTML，其次取纯文本，并转成 Markdown"""
    html_content = None
    text_content = None

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get('Content-Disposition') or "")
            if 'attachment' in disp:
                continue
            if ctype == "text/html":
                html_content = part.get_payload(decode=True).decode(errors="ignore")
                break  # 优先取第一个 HTML
            elif ctype == "text/plain" and not text_content:
                text_content = part.get_payload(decode=True).decode(errors="ignore")
    else:
        if msg.get_content_type() == "text/html":
            html_content = msg.get_payload(decode=True).decode(errors="ignore")
        elif msg.get_content_type() == "text/plain":
            text_content = msg.get_payload(decode=True).decode(errors="ignore")

    # 转成 Markdown
    if html_content:
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0  # 不自动换行
        md_text = h.handle(html_content).strip()
        return md_text
    elif text_content:
        return text_content.strip()
    else:
        return "(无内容)"

def process_mail():
    """连接邮箱并处理未读邮件"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")
        logger.debug("成功连接到邮箱服务器")

        # 搜索发件人 + 未读邮件
        status, data = mail.search(None, f'(UNSEEN FROM "{SENDER_FILTER}")')
        if status != "OK":
            logger.error("搜索邮件失败")
            return

        mail_ids = data[0].split()
        if not mail_ids:
            logger.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 没有新邮件")
            return
            
        logger.info(f"找到 {len(mail_ids)} 封未读邮件，开始处理...")

        for num in mail_ids:
            status, msg_data = mail.fetch(num, '(RFC822)')
            if status != "OK":
                logger.warning(f"无法获取邮件 {num.decode()}")
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            
            # 精确验证发件人
            from_header = msg.get("From", "")
            _, actual_sender = email.utils.parseaddr(from_header)
            
            logger.debug(f"处理邮件: 主题: {msg.get('Subject', '无主题')} | 发件人: {actual_sender}")
            
            # 验证发件人是否匹配
            if actual_sender != SENDER_FILTER:
                logger.info(f"跳过非目标发件人: {actual_sender} (期望: {SENDER_FILTER})")
                # 标记为已读避免重复处理
                mail.store(num, '+FLAGS', '\\Seen')
                continue

            # 主题解码
            subject = ""
            subject_header = email.header.decode_header(msg["Subject"])
            for part, encoding in subject_header:
                if isinstance(part, bytes):
                    try:
                        subject += part.decode(encoding or "utf-8", errors="ignore")
                    except:
                        subject += part.decode("latin1", errors="ignore")
                else:
                    subject += str(part)

            # 正文解析（Markdown 格式） - 修复：添加了 msg 参数
            content_md = extract_email_content(msg)  # 这里添加了 msg 参数
            
            # 添加邮件元信息
            mail_info = f"**发件人**: {actual_sender}  \n"
            mail_info += f"**时间**: {msg.get('Date', '未知时间')}  \n"
            mail_info += f"**收件人**: {msg.get('To', '未知')}  \n\n"
            full_content = mail_info + content_md

            # 推送到钉钉
            send_to_ding_markdown(subject, full_content)

            # 标记已读
            mail.store(num, '+FLAGS', '\\Seen')
            logger.info(f"邮件处理完成并标记为已读: {subject}")

        mail.logout()
        logger.debug("邮箱连接已关闭")
    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP错误: {e}")
    except Exception as e:
        logger.exception(f"处理邮件时发生异常: {e}")

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("启动腾讯企业邮箱 → 钉钉推送服务")
    logger.info(f"监控发件人: {SENDER_FILTER}")
    logger.info(f"检查间隔: {CHECK_INTERVAL}秒")
    logger.info(f"日志级别: {logging.getLevelName(LOG_LEVEL)}")
    logger.info("=" * 50)
    
    try:
        while True:
            start_time = time.time()
            process_mail()
            
            # 计算实际等待时间，确保间隔准确
            elapsed = time.time() - start_time
            if elapsed < CHECK_INTERVAL:
                sleep_time = CHECK_INTERVAL - elapsed
                logger.debug(f"等待 {sleep_time:.2f} 秒后再次检查...")
                time.sleep(sleep_time)
            else:
                logger.warning(f"处理时间过长 ({elapsed:.2f}秒)，将立即进行下一次检查")
    except KeyboardInterrupt:
        logger.info("用户中断程序，正在退出...")
    except Exception as e:
        logger.exception("程序发生未处理异常")
    finally:
        logger.info("程序已退出")
        logger.info("=" * 50)
