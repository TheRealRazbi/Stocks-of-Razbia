from quart import Quart, render_template, request, flash
import database
from wtforms import validators
from config_server.forms import SettingForm

app = Quart(__name__, static_folder="static/static")
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@app.route('/')
async def home():
    return await render_template("home.html")


@app.route('/list_company')
async def list_companies():
    session = database.Session()
    companies = session.query(database.Company).order_by(database.Company.price_diff.desc()).all()
    return await render_template("companies.html", companies=companies)


@app.route('/settings', methods=['GET', 'POST'])
async def settings():
    form_data = None
    if request.method == 'POST':
        form_data = await request.form

    forms_ = []
    for setting_name, setting in app.overlord.settings.items():

        setting = setting[1](form_data, data={'value': setting[0]}, prefix=setting_name)
        setting.value.label = setting_name
        forms_.append(setting)

    if request.method == 'POST':
        session = database.Session()
        for setting_form in forms_:
            if setting_form.validate():
                app.overlord.settings[setting_form.value.label] = (setting_form.value.data, type(setting_form))
                setting = session.query(database.Settings).get(setting_form.value.label)
                setting.value = setting_form.value.data
                session.commit()
                await flash("Settings saved successfully")
            else:
                await flash("One or more")

    return await render_template("settings.html", forms_=forms_)
