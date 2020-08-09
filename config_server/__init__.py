import json
import time
from contextlib import suppress
from typing import Type, List, Optional

from quart import Quart, render_template, request, flash, redirect, url_for, websocket
import database
from wtforms import validators, Form, FieldList
from config_server.forms import SettingForm, SetupForm, StreamElementsTokenForm, CompaniesNames
import asyncio
import markdown2

app = Quart(__name__, static_folder="static/static")
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


def getattr_chain(obj, attr: List[str]):
    with suppress(AttributeError):
        for name in attr:
            obj = getattr(obj, name)
        return obj


async def get_form_data():
    if request.method == 'POST':
        return await request.form
    return None


@app.route('/')
async def home():
    if app.overlord.api.twitch_key_requires_refreshing:
        app.overlord.api.twitch_key_requires_refreshing = False
        app.overlord.api.twitch_key_just_refreshed = True
        return redirect("https://razbi.funcity.org/stocks-chat-minigame/twitch_login")

    if not app.overlord.api.tokens_ready:
        return redirect(url_for('setup'))

    app.overlord.api.console_buffer_done = []
    return await render_template("home.html", tokens_loaded=app.overlord.api.tokens_ready, started=app.overlord.started,
                                 currency_system=app.overlord.api.currency_system.capitalize())


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
                # if app.overlord.currency_name == 'streamlabs_local':
                #     app.overlord.api.send_chat_message("!connect_minigame")
                session.commit()
                if app.overlord.api.currency_system == 'streamlabs_local' and app.overlord.api.started:
                    app.overlord.api.send_chat_message('!connect_minigame')
                    app.overlord.api.ping_streamlabs_local()
                # if setup_form.currency_system.data != 'streamlabs' and setup_form.currency_system.data != 'stream_elements':
                #     await flash("I see you tried saving a system that isn't available yet. "
                #                 "I must warn you that the program will literally just crash if you start with the unavailable currency system.")
                await flash('Currency System saved successfully')
        if setup_form.validate() and setup_form.currency_name.data != app.overlord.currency_name:
            if currency_name_db := session.query(database.Settings).get('currency_name'):
                app.overlord.mark_dirty('currency_name')
                currency_name_db.value = setup_form.currency_name.data

                session.commit()

    chosen_key = ''
    if app.overlord.api.currency_system == 'streamlabs':
        chosen_key = app.overlord.api.streamlabs_key
    elif app.overlord.api.currency_system == 'stream_elements':
        chosen_key = app.overlord.api.stream_elements_key
    elif app.overlord.api.currency_system == 'streamlabs_local':
        chosen_key = 'I have to write something here I guess'

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
    form_data = await get_form_data()

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
                    if app.overlord.started and setting_form.value.label == 'streamlabs_local':
                        app.overlord.api.send_chat_message("!connect_minigame")
                        await app.overlord.api.ping_streamlabs_local()
            else:
                await flash(f"Settings unsaved. {setting_form.errors['value']}")

    return await render_template("settings.html", forms_=forms_)


@app.route('/settings/company_names', methods=['GET', 'POST'])
async def company_names():
    setting_name = "company_names"
    form_data = await get_form_data()
    session = database.Session()
    company_names_db: database.Settings = session.query(database.Settings).get(setting_name)
    if company_names_db:
        names = json.loads(company_names_db.value)
    else:
        names = [{"company_name": "Razbia", "abbv": "umm I dunno"}]

    form = CompaniesNames(form_data, data={"items": names})
    if request.method == "POST":
        field: Optional[FieldList]
        if "add_field" in form_data:
            field_path = form_data.get("add_field").split("-")
            field = getattr_chain(form, field_path)
            if field is not None:
                field.append_entry()
        elif "delete_field" in form_data:
            *field_path, field_num = form_data.get("delete_field").split("-")
            field = getattr_chain(form, field_path)
            if field is not None:
                field.entries = [
                    entry
                    for entry in field.entries
                    if not entry.id.endswith(f"-{field_num}")
                ]
        elif form.validate():
            if company_names_db and company_names_db.value != form.data['items']:
                company_names_db.value = json.dumps(form.data['items'])
                session.commit()
                app.overlord.load_names()
            await flash("Company names saved successfully.")
        else:
            await flash(form.errors)

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
    session = database.Session()
    await save_token(token=twitch_token, token_name='twitch_key', length=30, session=session)
    expires_in = request.args.getlist('expires_in')
    if expires_in:
        expires_at = str(int(time.time()) + int(expires_in[0]))
        expires_at_db = session.query(database.Settings).get('twitch_key_expires_at')
        if expires_at_db:
            expires_at_db.value = expires_at
        else:
            session.add(database.Settings(key='twitch_key_expires_at', value=expires_at))
        session.commit()

    if app.overlord.api.twitch_key_just_refreshed:
        app.overlord.api.twitch_key_just_refreshed = False
        print("Twitch Token refreshed.")
        return redirect(url_for('home'))

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

    return await render_template('generate_stream_elements_token.html', stream_elements_form=stream_elements_token_form,
                                 stream_elements_token=app.overlord.api.stream_elements_key)


@app.route('/web_sockets_stuff')
async def web_sockets_stuff():
    return await render_template('web_sockets_stuff.html')


@app.route('/about')
async def about():
    return await render_template('about.html')


def escape_word(text: str, word: str):
    return text.replace(f'<{word}>', f'&lt;{word}&gt;')


def color_word_in_html(text: str, word: str, color: str):
    return text.replace(f'{word}', f'<span style="color: {color}">{word}</span>')


def color_multiple_words_in_html(text: str, words_and_colors: dict):
    for word, color in words_and_colors.items():
        text = color_word_in_html(text, word, color)
    return text


@app.route('/introduction')
async def introduction():
    try:
        with open('introduction.md', 'r') as f:
            intro = f.read()
    except FileNotFoundError:
        with open('lib/code/introduction.md', 'r') as f:
            intro = f.read()
    intro = escape_word(intro, 'company')
    intro = escape_word(intro, 'amount')
    mark_downer = markdown2.Markdown(extras=["break-on-newline"])
    intro = mark_downer.convert(intro)
    intro = color_multiple_words_in_html(intro,
                                         {
                                            'companies': '#dbce37',
                                            'company': '#dbce37',
                                            'users': '#923eed',
                                            'user': '#923eed',
                                            'my': '#5587f2',
                                            'stocks': '#3e9ef7',
                                            'buy': '#31e05a',
                                            'sell': '#e09a31',
                                            'points': '#31e06b',
                                            'currency': '#31e06b',
                                          }
                                         )

    return await render_template('introduction.html', intro=intro)


@app.websocket('/ws')
async def ws():
    while True:
        if app.overlord.api.console_buffer != app.overlord.api.console_buffer_done:
            res = "\n".join(app.overlord.api.console_buffer)
            app.overlord.api.console_buffer_done = app.overlord.api.console_buffer.copy()
            await websocket.send(res)
        else:
            await asyncio.sleep(.5)


@app.websocket('/streamlabs')
async def streamlabs_ws():
    while True:
        if app.overlord.api.streamlabs_local_send_buffer:
            message_to_send = app.overlord.api.streamlabs_local_send_buffer
            await websocket.send(message_to_send)
            # print(f'sent: {message_to_send}')
            data = await websocket.receive()
            # print(f'received: {data}')
            app.overlord.api.streamlabs_local_receive_buffer = data
            app.overlord.api.streamlabs_local_send_buffer = ''
        await asyncio.sleep(.1)

