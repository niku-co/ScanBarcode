from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import logging
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # برای استفاده از session

# مسیر فایل لاگ
log_path = os.path.join('templates', 'logs.txt')
os.makedirs(os.path.dirname(log_path), exist_ok=True)

# تنظیمات لاگر
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

@app.route('/')
def index():
    logging.info("نمایش صفحه اصلی")
    return render_template('index.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    message = None
    error = None

    if request.method == 'POST':
        server_address = request.form.get('setting1')
        username = request.form.get('setting2')
        password = request.form.get('setting3')

        session['form_data'] = {
            'setting1': server_address,
            'setting2': username,
            'setting3': password
        }

        if not server_address or not username or not password:
            error = "لطفا تمام فیلدها را پر کنید!"
            logging.warning("فیلدهای تنظیمات ناقص وارد شده‌اند")
        else:
            try:
                url = f"{server_address}/users?password={password}"
                logging.info(f"در حال ارسال درخواست به API: {url}")
                response = requests.get(url)

                if response.status_code == 200:
                    result = response.json()
                    logging.info(f"پاسخ دریافتی از سرور: {result}")

                    if result and isinstance(result, list) and len(result) > 0:
                        if "پسورد درست است" in result[0] and result[0]["پسورد درست است"] == "Yes":
                            message = "پسورد درست است! اطلاعات با موفقیت ذخیره شد."
                            logging.info("احراز هویت موفق")
                        else:
                            error = "پسورد نادرست است!"
                            logging.warning("پسورد اشتباه وارد شده")
                    else:
                        error = "پاسخ سرور نامعتبر است!"
                        logging.error("پاسخ نامعتبر از سرور دریافت شد")
                else:
                    error = "خطا در ارتباط با سرور!"
                    logging.error(f"خطا در وضعیت پاسخ سرور: {response.status_code}")
            except Exception as e:
                logging.exception("خطا در ارتباط با سرور:")
                error = "خطا در ارسال درخواست به سرور!"

    form_data = session.get('form_data', {})
    return render_template('settings.html', message=message, error=error, form_data=form_data)

@app.route('/scan', methods=['POST'])
def scan():
    code = request.form.get('code')
    logging.info(f"کد دریافت شده برای اسکن: {code}")

    if not code or not code.isdigit() or len(code) < 10:
        flash("❌ کد باید فقط عدد و حداقل ۱۰ رقم باشد!", "danger")
        logging.warning("کد نامعتبر وارد شده")
        return redirect(url_for('index'))

    prefs = session.get('form_data')
    if not prefs:
        flash("❌ ابتدا تنظیمات را وارد کنید!", "warning")
        logging.warning("تنظیمات موجود نیست")
        return redirect(url_for('index'))

    server_address = prefs.get('setting1')
    api_url = f"{server_address}/barcod?barcod={code}"
    logging.info(f"در حال ارسال درخواست اسکن به: {api_url}")

    try:
        response = requests.get(api_url)
        if response.status_code != 200:
            flash("❌ خطا در دریافت اطلاعات از سرور!", "danger")
            logging.error("پاسخ ناموفق در اسکن بارکد")
            return redirect(url_for('index'))

        json_data = response.json()
        delivery_time = json_data.get('DeliveryTime')
        logging.info(f"اطلاعات دریافتی: {json_data}")

        if delivery_time == "NULL":
            order_id = json_data.get('OrderID')
            if order_id:
                update_url = f"{server_address}/update-delivery?OrderID={order_id}"
                update_response = requests.get(update_url)
                if update_response.status_code != 200:
                    flash("❌ خطا در به‌روزرسانی زمان تحویل!", "danger")
                    logging.error("به‌روزرسانی زمان تحویل با خطا مواجه شد")
                    return redirect(url_for('index'))
        elif delivery_time:
            flash("⚠️ این کد قبلاً ثبت شده است.", "warning")
            logging.info("بارکد تکراری")
            return redirect(url_for('index'))

        quantity_str = json_data.get('Quantity')
        if quantity_str:
            try:
                quantity = float(quantity_str)
                flash(f"✅ مقدار موجود در انبار: {quantity}", "success")
                logging.info(f"مقدار انبار: {quantity}")
            except ValueError:
                flash("⚠️ خطا در خواندن مقدار موجودی!", "warning")
                logging.warning("مقدار Quantity نامعتبر بود")
        else:
            flash("⚠️ مقدار Quantity وجود ندارد!", "warning")
            logging.warning("Quantity در پاسخ وجود نداشت")

        return redirect(url_for('index'))

    except Exception as e:
        flash("❌ خطا در پردازش بارکد!", "danger")
        logging.exception("خطا در پردازش بارکد:")
        return redirect(url_for('index'))

@app.route('/clear_session')
def clear_session():
    logging.info("جلسه پاک شد")
    #session.pop('form_data', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
