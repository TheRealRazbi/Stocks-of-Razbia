import webbrowser

from quart import Quart, render_template, request, flash, redirect, url_for
import database
from wtforms import validators
from config_server.forms import SettingForm, SetupForm
import pickle

app = Quart(__name__, static_folder="static/static")
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@app.route('/')
async def home():
    # print(app.overlord.api.tokens_ready)
    if not app.overlord.api.tokens_ready:
        return redirect(url_for('setup'))
    return await render_template("home.html")


@app.route('/setup', methods=['GET', 'POST'])
async def setup():
    form_data = None
    if request.method == 'POST':
        form_data = await request.form

    setup_form = SetupForm(form_data, data={'currency_system': app.overlord.api.currency_system,
                                            'currency_name': app.overlord.currency_name})
    if request.method == 'POST':
        session = database.Session()
        if setup_form.currency_system.data and setup_form.currency_system.data != app.overlord.api.currency_system:
            if currency_system_db := session.query(database.Settings).get('currency_system'):
                app.overlord.api.mark_dirty('currency_system')
                currency_system_db.value = setup_form.currency_system.data
                session.commit()
        if setup_form.validate() and setup_form.currency_name.data != app.overlord.currency_name:
            if currency_name_db := session.query(database.Settings).get('currency_name'):
                app.overlord.mark_dirty('currency_name')
                currency_name_db.value = setup_form.currency_name.data
                session.commit()
        # if setup_form.errors:
        #     await flash(f"Settings unsaved. {[(error.capitalize(), setup_form.errors[error]) for error in setup_form.errors]}")

    # print(dir(setup_form.currency_system))
    # print(setup_form.currency_system.data)
    # print(app.overlord.api.tokens_ready)
    return await render_template('setup.html', setup_form=setup_form, tokens_loaded=app.overlord.api.tokens_ready)


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

        setting = setting(form_data, data={'value': getattr(app.overlord, setting_name)}, prefix=setting_name)
        setting.value.label = setting_name
        forms_.append(setting)

    if request.method == 'POST':
        session = database.Session()
        for setting_form in forms_:
            if setting_form.validate():
                if setting_form.value.data != getattr(app.overlord, setting_form.value.label):
                    await flash(f"Setting '{setting_form.value.label}' saved successfully with the value '{setting_form.value.data}'")
                    app.overlord.mark_dirty(setting_form.value.label)
                    setting = session.query(database.Settings).get(setting_form.value.label)
                    setting.value = setting_form.value.data
                    session.commit()
            else:
                await flash(f"Settings unsaved. {setting_form.errors['value']}")

    return await render_template("settings.html", forms_=forms_)


@app.route('/settings/company_names', methods=['GET', 'POST'])
async def company_names():
    names = []
    with open("lib/code/company_names.txt", "r") as f:
        for line in f:
            line = line.strip().split('|')
            temp = []
            for element in line:
                temp.append(element)
            names.append(temp)

    return await render_template("company_names.html", names=names)


@app.route('/settings/api/', methods=['GET'])
async def token_settings():
    return await render_template('api_settings.html',
                                 streamlabs_token=app.overlord.api.streamlabs_key,
                                 twitch_token=app.overlord.api.twitch_key)


async def save_token(token, token_name, length, session=None):
    if token and len(token[0]) == length:
        token = token[0]
        setattr(app.overlord.api, token_name, token)
        if session is None:
            session = database.Session()
        token_db = session.query(database.Settings).get(token_name)
        if token_db:
            token_db.value = token
        else:
            token_db = database.Settings(key=token_name, value=token)
            session.add(token_db)
        session.commit()
        if app.overlord.api.streamlabs_key and app.overlord.api.twitch_key and app.overlord.api.currency_system:
            app.overlord.api.tokens_ready = True

        return f"{token_name} saved successfully"


@app.route('/settings/api/twitch_token/')
async def load_twitch_token():
    twitch_token = request.args.getlist('access_token')
    # print(twitch_token)
    await save_token(token=twitch_token, token_name='twitch_key', length=30)

    return redirect(url_for('token_settings'))


@app.route('/settings/api/streamlabs_token/')
async def load_streamlabs_token():
    streamlabs_token = request.args.getlist('access_token')
    await save_token(token=streamlabs_token, token_name='streamlabs_key', length=40)

    return redirect(url_for('token_settings'))


@app.route('/settings/api/streamlabs_token/generate_token/')
async def generate_streamlabs_token():
    # return redirect("https://streamlabs.com/api/v1.0/authorize?response_type=code&client_id=vLylBKwHLDIPfhUkOKexM2f6xhLe7rqmKJaeU0kB&redirect_uri=https://razbi.funcity.org/stocks-chat-minigame/streamlabs_login&scope=points.read+points.write")
    return redirect("https://razbi.funcity.org/stocks-chat-minigame/streamlabs_login")


@app.route('/settings/api/twitch_token/generate_token/')
async def generate_twitch_token():
    # return redirect("https://id.twitch.tv/oauth2/authorize?client_id=q4nn0g7b07xfo6g1lwhp911spgutps&redirect_uri=https://razbi.funcity.org/stocks-chat-minigame/twitch_login&response_type=code&scope=chat:read+chat:edit")
    return redirect("https://razbi.funcity.org/stocks-chat-minigame/twitch_login")

    # @app.route('/settings/api/twitch_token')
# async def this_does_nothing():
#     webbrowser.open("https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=q4nn0g7b07xfo6g1lwhp911spgutps&redirect_uri=http://localhost:5000/settings/api&scope=openid")
#
#     return "literally nothing"


# @app.route('/settings/api/streamlabs_token')
# async def this_does_nothing_as_well():
    # webbrowser.open(
    #     "https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=tq8sa9mxrrnt95mbk332lyjht3nzsh&redirect_uri=https://razbi.funcity.org/notification-centre/tokengen/&scope=openid")

    # return "literally nothing"

