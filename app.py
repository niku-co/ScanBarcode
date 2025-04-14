from flask import Flask, render_template, request, redirect, url_for, session , flash
import requests
import json
import os

app = Flask(__name__)
app.secret_key = 'SAf4dsg#45hK4yyh145'  # برای استفاده از session
SETTINGS_FILE = 'settings.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_settings(data):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    message = None
    error = None

    # بارگذاری تنظیمات قبلی از فایل
    form_data = load_settings()

    if request.method == 'POST':
        # دریافت داده‌ها از فرم
        server_address = request.form.get('serveraddress')
        username = request.form.get('username')
        password = request.form.get('password')

        # بررسی پر بودن فیلدها
        if not server_address or not username or not password:
            error = "لطفا تمام فیلدها را پر کنید!"
        else:
            # بررسی پسورد از API
            try:
                url = f"{server_address}/users?password={password}"
                response = requests.get(url)

                if response.status_code == 200:
                    result = response.json()
                    print("پاسخ سرور:", result)

                    found = False
                    if result and isinstance(result, list):
                        for item in result:
                            if "پسورد درست است" in item and item["پسورد درست است"] == "Yes":
                                found = True
                                break

                    if found:
                        message = "پسورد درست است! اطلاعات با موفقیت ذخیره شد."
                        form_data = {
                            'serveraddress': server_address,
                            'username': username,
                            'password': password
                        }
                        save_settings(form_data)  # ذخیره در فایل
                    else:
                        error = "پسورد نادرست است!"
                else:
                    error = "خطا در ارتباط با سرور!"
            except Exception as e:
                error = "خطا در ارسال درخواست به سرور!"

    return render_template('settings.html', message=message, error=error, form_data=form_data)

@app.route('/scan', methods=['POST'])
def scan():
    code = request.form.get('code')
    if not code or not code.isdigit() or len(code) < 10:
        flash("❌ کد باید فقط عدد و حداقل ۱۰ رقم باشد!", "danger")
        return redirect(url_for('index'))

    prefs = load_settings()
    if not prefs or 'serveraddress' not in prefs:
        flash("❌ ابتدا تنظیمات را وارد کنید!", "warning")
        return redirect(url_for('index'))

    server_address = prefs.get('serveraddress')
    api_url = f"{server_address}/barcod?barcod={code}"

    try:
        response = requests.get(api_url)
        if response.status_code != 200:
            flash("❌ خطا در دریافت اطلاعات از سرور!", "danger")
            return redirect(url_for('index'))

        json_data = response.json()
        delivery_time = json_data.get('DeliveryTime')

        if delivery_time == "NULL":
            order_id = json_data.get('OrderID')
            if order_id:
                update_url = f"{server_address}/update-delivery?OrderID={order_id}"
                update_response = requests.get(update_url)
                if update_response.status_code != 200:
                    flash("❌ خطا در به‌روزرسانی زمان تحویل!", "danger")
                    return redirect(url_for('index'))
        elif delivery_time:
            flash("⚠️ این کد قبلاً ثبت شده است.", "warning")
            return redirect(url_for('index'))

        # دریافت GoodID
        good_id = json_data.get('GoodID')
        if not good_id:
            flash("⚠️ مقدار GoodID پیدا نشد!", "warning")
            return redirect(url_for('index'))

        # درخواست به API دوم برای گرفتن موجودی اصلی
        quantity_api_url = f"{server_address}/get-quantity?GoodID={good_id}"
        quantity_response = requests.get(quantity_api_url)
        if quantity_response.status_code != 200:
            flash("❌ خطا در دریافت مقدار موجودی!", "danger")
            return redirect(url_for('index'))

        quantity_data = quantity_response.json()
        quantity_str = quantity_data.get('Quantity')
        if quantity_str:
            try:
                quantity = float(quantity_str)
                flash(f"✅ مقدار موجود در انبار: {quantity}", "success")
            except ValueError:
                flash("⚠️ خطا در تبدیل مقدار موجودی!", "warning")
        else:
            flash("⚠️ مقدار Quantity یافت نشد!", "warning")

        return redirect(url_for('index'))

    except Exception as e:
        flash("❌ خطا در پردازش بارکد!", "danger")
        return redirect(url_for('index'))

@app.route('/clear_session')
def clear_session():
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
