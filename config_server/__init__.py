import json
from contextlib import suppress
from typing import Type, List, Optional

from quart import Quart, render_template, request, flash, redirect, url_for, websocket
import database
from wtforms import validators, Form, FieldList
from config_server.forms import SettingForm, SetupForm, StreamElementsTokenForm, CompaniesNames
import pickle
import asyncio

app = Quart(__name__, static_folder="static/static")
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


def getattr_chain(obj, attr: List[str]):
    with suppress(AttributeError):
        for name in attr:
            obj = getattr(obj, name)
        return obj


async def get_formdata():
    if request.method == 'POST':
        return await request.form
    return None


@app.route('/')
async def home():
    if app.overlord.api.twitch_key_requires_refreshing:
        app.overlord.api.twitch_key_requires_refreshing = False
        return redirect("https://razbi.funcity.org/stocks-chat-minigame/twitch_login")

    if not app.overlord.api.tokens_ready:
        return redirect(url_for('setup'))

    return await render_template("home.html", tokens_loaded=app.overlord.api.tokens_ready, started=app.overlord.started)


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
                if setup_form.currency_system.data != 'streamlabs' and setup_form.currency_system.data != 'stream_elements':
                    await flash("I see you tried saving a system that isn't available yet. "
                                "I must warn you that the program will literally just crash if you start with the unavailable currency system.")
                await flash('Currency System saved successful')
        if setup_form.validate() and setup_form.currency_name.data != app.overlord.currency_name:
            if currency_name_db := session.query(database.Settings).get('currency_name'):
                app.overlord.mark_dirty('currency_name')
                currency_name_db.value = setup_form.currency_name.data
                session.commit()

        # if app.overlord.api.streamlabs_key and app.overlord.api.twitch_key and app.overlord.api.currency_system and\
        #         app.overlord.api.validate_twitch_token():
        #     app.overlord.api.tokens_ready = True

        # if setup_form.errors:
        #     await flash(f"Settings unsaved. {[(error.capitalize(), setup_form.errors[error]) for error in setup_form.errors]}")

    # print(dir(setup_form.currency_system))
    # print(setup_form.currency_system.data)
    # print(app.overlord.api.tokens_ready)
    chosen_key = ''
    if app.overlord.api.currency_system == 'streamlabs':
        chosen_key = app.overlord.api.streamlabs_key
    elif app.overlord.api.currency_system == 'stream_elements':
        chosen_key = app.overlord.api.stream_elements_key
    return await render_template('setup.html', setup_form=setup_form, tokens_loaded=app.overlord.api.tokens_ready,
                                 twitch_key=app.overlord.api.twitch_key, chosen_key=chosen_key,
                                 currency_system=app.overlord.api.currency_system)


@app.route('/start_minigame')
async def start_minigame():
    app.overlord.api.started = True
    app.overlord.started = True
    return redirect(url_for('home'))


@app.route('/list_company')
async def list_companies():
    session = database.Session()
    companies = session.query(database.Company).order_by(database.Company.price_diff.desc()).all()
    return await render_template("companies.html", companies=companies)


@app.route('/settings', methods=['GET', 'POST'])
async def settings():
    form_data = await get_formdata()

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
    setting_name = "company_names"
    formdata = await get_formdata()
    session = database.Session()
    obj: database.Settings = session.query(database.Settings).get(setting_name)
    if obj:
        names = json.loads(obj.value)
    else:
        # TODO: get defaults
        names = [{"company_name": "French keyboards", "abbv": "azerty"}]
    form = CompaniesNames(formdata, data={"items": names})
    if request.method == "POST":
        field: Optional[FieldList]
        if "add_field" in formdata:
            field_path = formdata.get("add_field").split("-")
            field = getattr_chain(form, field_path)
            if field is not None:
                field.append_entry()
        elif "delete_field" in formdata:
            *field_path, field_num = formdata.get("delete_field").split("-")
            field = getattr_chain(form, field_path)
            if field is not None:
                field.entries = [
                    entry
                    for entry in field.entries
                    if not entry.id.endswith(f"-{field_num}")
                ]
        elif form.validate():
            # TODO: Bruh handle saving of the data
            pass
    return await render_template("company_names.html", form=form)


@app.route('/settings/api/', methods=['GET'])
async def token_settings():
    return await render_template('api_settings.html',
                                 streamlabs_token=app.overlord.api.streamlabs_key,
                                 twitch_token=app.overlord.api.twitch_key,
                                 stream_elements_token=app.overlord.api.stream_elements_key,
                                 currency_system=app.overlord.api.currency_system)


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
        # if app.overlord.api.streamlabs_key and app.overlord.api.twitch_key and app.overlord.api.currency_system and\
        #         app.overlord.api.validate_twitch_token():
        #     app.overlord.api.tokens_ready = True

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
    return redirect("https://razbi.funcity.org/stocks-chat-minigame/streamlabs_login")


@app.route('/settings/api/twitch_token/generate_token/')
async def generate_twitch_token():
    return redirect("https://razbi.funcity.org/stocks-chat-minigame/twitch_login")


@app.route('/settings/api/stream_elements_token/generate_token/', methods=['GET', 'POST'])
async def generate_stream_elements_token():
    # return redirect("https://razbi.funcity.org/stocks-chat-minigame/stream_elements_login")
    form_data = None
    if request.method == 'POST':
        form_data = await request.form
    stream_elements_token_form = StreamElementsTokenForm(form_data)
    if request.method == 'POST':
        if stream_elements_token_form.validate():
            # stream_elements_token = StreamElementsTokenForm.token.data
            session = database.Session()
            stream_elements_token_db = session.query(database.Settings).get('stream_elements_key')
            if stream_elements_token_db:
                stream_elements_token_db.value = stream_elements_token_form.token.data
            else:
                session.add(database.Settings(key='stream_elements_key', value=stream_elements_token_form.token.data))
            session.commit()
            app.overlord.api.stream_elements_key = stream_elements_token_form.token.data
            await flash("StreamElements token saved successfully.")

    return await render_template('generate_stream_elements_token.html', stream_elements_form=stream_elements_token_form)


@app.route('/web_sockets_stuff')
async def web_sockets_stuff():
    return await render_template('web_sockets_stuff.html')


# @app.websocket('/ws')
# async def ws():
#     while True:
#         data = await websocket.receive()
#         await websocket.send(data)
#         print(data)

@app.websocket('/ws')
async def ws():
    while True:
        # data = await websocket.receive()
        # await websocket.send(f"echo {data}")
        try:
            await websocket.send(app.overlord.api.console_buffer.pop(0))
        except IndexError:
            await asyncio.sleep(1.5)


@app.websocket('/streamlabs')
async def streamlabs_ws():
    while True:
        await websocket.send('REEEEE')
        data = await websocket.receive()
        # await websocket.send(f"echo {data}")
        print(f'received: {data}')
        print(f'sent: REEEE')
        await asyncio.sleep(5)
