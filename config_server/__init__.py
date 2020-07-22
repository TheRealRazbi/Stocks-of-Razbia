import webbrowser

from quart import Quart, render_template, request, flash, redirect, url_for
import database
from wtforms import validators
from config_server.forms import SettingForm
import pickle

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


@app.route('/settings/api', methods=['GET'])
async def token_settings():
    print(request.args)
    # print(request.args.getlist('code')[0])
    twitch_token = request.args.getlist('twitch_token')
    streamlabs_token = request.args.getlist('streamlabs_token')
    if twitch_token and len(twitch_token[0]) == 36:
        twitch_token = twitch_token[0]
        app.overlord.api.twitch_key = twitch_token
        with open("lib/twitch_key", "wb") as f:
            pickle.dump(twitch_token, f)
        await flash("Twitch token saved successfully")
    if streamlabs_token and len(streamlabs_token[0]) == 40:
        streamlabs_token = streamlabs_token[0]
        app.overlord.api.streamlabs_token = streamlabs_token
        with open("lib/streamlabs_key", "wb") as f:
            pickle.dump(streamlabs_token, f)
        await flash("Streamlabs token saved successfully")

    # return redirect(url_for('home'))
    return await render_template('api_settings.html')


@app.route('/settings/api/twitch_token')
async def this_does_nothing():
    webbrowser.open("https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=q4nn0g7b07xfo6g1lwhp911spgutps&redirect_uri=http://localhost:5000/settings/api&scope=openid")

    return "literally nothing"


@app.route('/settings/api/streamlabs_token')
async def this_does_nothing_as_well():
    # webbrowser.open(
    #     "https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=tq8sa9mxrrnt95mbk332lyjht3nzsh&redirect_uri=https://razbi.funcity.org/notification-centre/tokengen/&scope=openid")

    return "literally nothing"

