#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import threading
import os

# ========== НАСТРОЙКИ ПОЧТЫ (замените на свои) ==========
EMAIL_CONFIG = {
    'smtp_server': 'smtp.mail.ru',
    'smtp_port': 587,
    'sender_email': 'kerim.bayramukov@mail.ru',   # ваша почта
    'sender_password': 'g7IQG4oXFVjwXCVa6gOS',     # пароль приложения
    'manager_email': 'kerimbajramukov015@gmail.com'  # куда дублировать заказы
}

def send_email(to_email, subject, html_content, text_content=None):
    try:
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"DZHAM CAKE <{EMAIL_CONFIG['sender_email']}>"
        msg['To'] = to_email
        if text_content:
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        server.send_message(msg)
        server.quit()
        print(f"   [OK] Письмо отправлено на {to_email}")
        return True
    except Exception as e:
        print(f"   [ERR] Ошибка отправки: {e}")
        return False

def render_base_template(title, content_html):
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:20px;background:#f5f5f5;font-family:'Segoe UI',Arial,sans-serif;">
        <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:28px;overflow:hidden;box-shadow:0 12px 28px rgba(0,0,0,0.05);">
            <div style="padding:28px 24px 12px;text-align:center;border-bottom:2px solid #f0f0f0;">
                <div style="font-size:28px;font-weight:800;">DZHAM CAKE</div>
            </div>
            <div style="padding:24px;">
                <div style="font-size:22px;font-weight:600;margin-bottom:16px;">{title}</div>
                {content_html}
            </div>
            <div style="background:#fafafa;padding:16px;text-align:center;font-size:12px;color:#999;">DZHAM CAKE</div>
        </div>
    </body>
    </html>
    """

def client_order_card(order_data):
    items_rows = "".join(f"<tr><td>{i['name']}</td><td style='text-align:center'>x{i['qty']}</td><td style='text-align:right'>{i['line_sum']} руб.</td></tr>" for i in order_data['items'])
    content = f"""
    <div style="margin-bottom:20px;">
        <div style="font-size:18px;font-weight:700;">Заказ №{order_data['orderNumber']}</div>
        <div style="font-size:13px;color:#777;">{order_data['timestamp']}</div>
    </div>
    <div style="background:#f8f8f8;border-radius:20px;padding:16px;margin-bottom:20px;">
        <div><strong>Получатель:</strong> {order_data['client_name']}</div>
        <div><strong>Телефон:</strong> {order_data['client_phone']}</div>
        <div><strong>Оплата:</strong> {order_data['payment_method']}</div>
    </div>
    <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">{items_rows}</table>
    <div style="text-align:right;font-size:18px;font-weight:800;">Итого: {order_data['total']} руб.</div>
    <p style="margin-top:20px;">Спасибо за заказ! Когда он будет готов, мы свяжемся с вами.</p>
    """
    return render_base_template("Ваш заказ принят!", content)

def manager_order_card(order_data):
    items_list = "\n".join([f"   {i['name']}  |  x{i['qty']}  |  {i['line_sum']} руб." for i in order_data['items']])
    content = f"""
    <div style="background:#f8f8f8;border-radius:20px;padding:16px;margin-bottom:20px;">
        <div><strong>Номер заказа:</strong> {order_data['orderNumber']}</div>
        <div><strong>Время:</strong> {order_data['timestamp']}</div>
        <div><strong>Клиент:</strong> {order_data['client_name']} ({order_data['client_phone']})</div>
        <div><strong>Email:</strong> {order_data['client_email']}</div>
        <div><strong>Оплата:</strong> {order_data['payment_method']}</div>
    </div>
    <div style="background:#f0f0f2;border-radius:20px;padding:16px;">
        <strong>Состав заказа</strong>
        <pre style="margin:10px 0 0 0;font-family:monospace;">{items_list}</pre>
    </div>
    <div style="margin-top:20px;text-align:right;font-size:18px;font-weight:800;">ИТОГО: {order_data['total']} руб.</div>
    """
    return render_base_template("НОВЫЙ ЗАКАЗ", content)

def client_cancel_card(order_data):
    content = f"""
    <div style="margin-bottom:20px;">
        <div style="font-size:18px;font-weight:700;">Заказ №{order_data['orderNumber']} отменён</div>
        <div style="margin-top:10px;padding:10px;background:#f8f8f8;border-radius:20px;">
            <div><strong>Состав:</strong> {', '.join([f'{i["name"]} x{i["qty"]}' for i in order_data['items']])}</div>
            <div><strong>Сумма:</strong> {order_data['total']} руб.</div>
        </div>
    </div>
    <p>Деньги не списаны. Если вы хотите сделать новый заказ, мы всегда рады вас видеть!</p>
    """
    return render_base_template("Заказ отменён", content)

def manager_cancel_card(order_data):
    content = f"""
    <div style="background:#f8f8f8;border-radius:20px;padding:16px;margin-bottom:20px;">
        <div><strong>Номер заказа:</strong> {order_data['orderNumber']}</div>
        <div><strong>Клиент:</strong> {order_data['client_name']}</div>
        <div><strong>Телефон:</strong> {order_data['client_phone']}</div>
        <div><strong>Email:</strong> {order_data['client_email']}</div>
        <div><strong>Состав:</strong> {', '.join([f'{i["name"]} x{i["qty"]}' for i in order_data['items']])}</div>
        <div><strong>Сумма:</strong> {order_data['total']} руб.</div>
    </div>
    <p>Заказ отменён клиентом.</p>
    """
    return render_base_template("ОТМЕНА ЗАКАЗА", content)

def manager_review_card(review_data):
    content = f"""
    <div style="background:#f8f8f8;border-radius:20px;padding:16px;margin-bottom:20px;">
        <div><strong>Клиент:</strong> {review_data['client_name']}</div>
        <div><strong>Email:</strong> {review_data['client_email']}</div>
        <div><strong>Оценка:</strong> {review_data['rating']}/5</div>
        <div><strong>Отзыв:</strong><br>"{review_data['review']}"</div>
    </div>
    """
    return render_base_template("НОВЫЙ ОТЗЫВ", content)

def send_order_notifications(order_data):
    send_email(order_data['client_email'], f"Заказ №{order_data['orderNumber']} принят", client_order_card(order_data))
    send_email(EMAIL_CONFIG['manager_email'], f"НОВЫЙ ЗАКАЗ №{order_data['orderNumber']}", manager_order_card(order_data))

def send_cancel_notifications(order_data):
    send_email(order_data['client_email'], f"Заказ №{order_data['orderNumber']} отменён", client_cancel_card(order_data))
    send_email(EMAIL_CONFIG['manager_email'], f"ОТМЕНА ЗАКАЗА №{order_data['orderNumber']}", manager_cancel_card(order_data))

def send_review_notification(review_data):
    send_email(EMAIL_CONFIG['manager_email'], f"Новый отзыв от {review_data['client_name']}", manager_review_card(review_data))

# ========== HTTP СЕРВЕР ==========
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            try:
                with open('index.html', 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(f.read())
            except:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        data = json.loads(body.decode('utf-8'))
        if self.path == '/log':
            typ = data.get('type')
            info = data.get('data')
            ts = datetime.now().strftime('%H:%M:%S')
            
            if typ == 'REGISTRATION':
                print(f"\n{BLUE}[ РЕГИСТРАЦИЯ {ts} ]{RESET}")
                print(f"   Email: {info.get('email')}")
                print(f"   ФИО: {info.get('fullname')}")
                print(f"   Телефон: {info.get('phone')}")
                
            elif typ == 'ORDER':
                print(f"\n{GREEN}[ ЗАКАЗ {ts} ]{RESET}")
                print(f"   Номер: {info.get('orderNumber')}")
                print(f"   Клиент: {info['user']['fullname']} | {info['user']['phone']} | {info['user']['email']}")
                for i in info['items']:
                    print(f"   - {i['name']} x{i['qty']} = {i['line_sum']} руб.")
                print(f"   ИТОГО: {info.get('total')} руб. | Оплата: {'Наличные' if info.get('paymentMethod')=='cash' else 'По телефону'}")
                
                order_data = {
                    'orderNumber': info['orderNumber'],
                    'timestamp': datetime.now().strftime('%d.%m.%Y %H:%M'),
                    'client_name': info['user']['fullname'],
                    'client_phone': info['user']['phone'],
                    'client_email': info['user']['email'],
                    'items': info['items'],
                    'total': info['total'],
                    'payment_method': 'Наличные при получении' if info['paymentMethod']=='cash' else 'Оплата по телефону'
                }
                threading.Thread(target=send_order_notifications, args=(order_data,)).start()
                
            elif typ == 'CANCEL':
                print(f"\n{RED}[ ОТМЕНА ЗАКАЗА {ts} ]{RESET}")
                print(f"   Номер: {info.get('orderNumber')} | Клиент: {info['user']['fullname']}")
                
                cancel_data = {
                    'orderNumber': info['orderNumber'],
                    'client_name': info['user']['fullname'],
                    'client_phone': info['user']['phone'],
                    'client_email': info['user']['email'],
                    'items': info.get('items', []),
                    'total': info.get('total', 0)
                }
                threading.Thread(target=send_cancel_notifications, args=(cancel_data,)).start()
                
            elif typ == 'REVIEW':
                print(f"\n{YELLOW}[ ОТЗЫВ {ts} ]{RESET}")
                print(f"   От {info['user']['fullname']}: {info.get('review')} (оценка {info.get('rating')})")
                
                review_data = {
                    'client_name': info['user']['fullname'],
                    'client_email': info['user']['email'],
                    'review': info.get('review'),
                    'rating': info.get('rating')
                }
                threading.Thread(target=send_review_notification, args=(review_data,)).start()
                
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("\n" + "="*55)
    print("   DZHAM CAKE СЕРВЕР ЗАПУЩЕН")
    print("="*55)
    print(f"   Сайт: http://0.0.0.0:{port}")
    print(f"   Логи заказов выводятся в этой консоли")
    print(f"   Почтовые уведомления включены")
    print("="*55 + "\n")
    try:
        server = HTTPServer(('0.0.0.0', port), Handler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[ СЕРВЕР ОСТАНОВЛЕН ]\n")
        server.server_close()