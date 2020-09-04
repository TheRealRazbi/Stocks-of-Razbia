import ast
import json
import time
from contextlib import suppress
from typing import Type, List, Optional

from quart import Quart, render_template, request, flash, redirect, url_for, websocket, current_app
import database
from wtforms import validators, Form, FieldList

from announcements import AnnouncementDict, Announcement
from config_server.forms import SettingForm, SetupForm, StreamElementsTokenForm, CompaniesNames, CommandNameForm, \
    CommandNamesForm, CommandMessagesForm, CommandMessagesRestoreDefaultForm, AnnouncementForm
import asyncio
import markdown2
import commands
from customizable_stuff import load_command_names, load_message_templates, load_announcements
from more_tools import BidirectionalMap

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

    if app.overlord.api.stream_elements_key_requires_refreshing:
        app.overlord.api.stream_elements_key_requires_refreshing = False
        app.overlord.api.stream_elements_key_just_refreshed = True
        return redirect("https://razbi.funcity.org/stocks-chat-minigame/streamelements_login")

    if not app.overlord.api.tokens_ready:
        return redirect(url_for('setup'))

    app.overlord.api.console_buffer_done = []
    return await render_template("home.html", tokens_loaded=app.overlord.api.tokens_ready, started=app.overlord.started,
                                 currency_system=app.overlord.api.currency_system.capitalize(), currency_name=app.overlord.currency_name)


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
                if app.overlord.api.currency_system == 'streamlabs_local' and app.overlord.api.started:
                    await app.overlord.api.ping_streamlabs_local()
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


@app.route('/customizations/company_names', methods=['GET', 'POST'])
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


@app.route('/settings/api/stream_elements_token/')
async def load_stream_elements_token():
    stream_elements = request.args.getlist('access_token')
    session = database.Session()
    await save_token(token=stream_elements, token_name='stream_elements_key', length=22, session=session)
    expires_in = request.args.getlist('expires_in')
    if expires_in:
        expires_at = str(int(time.time()) + int(expires_in[0]))
        expires_at_db = session.query(database.Settings).get('stream_elements_key_expires_at')
        if expires_at_db:
            expires_at_db.value = expires_at
        else:
            session.add(database.Settings(key='stream_elements_key_expires_at', value=expires_at))
        session.commit()

    if app.overlord.api.stream_elements_key_just_refreshed:
        app.overlord.api.stream_elements_key_just_refreshed = False
        print("Stream_elements Token refreshed.")
        return redirect(url_for('home'))

    return redirect(url_for('token_settings'))


@app.route('/settings/api/streamlabs_token/generate_token/')
async def generate_streamlabs_token():
    return redirect("https://razbi.funcity.org/stocks-chat-minigame/streamlabs_login")


@app.route('/settings/api/twitch_token/generate_token/')
async def generate_twitch_token():
    return redirect("https://razbi.funcity.org/stocks-chat-minigame/twitch_login")


@app.route('/settings/api/stream_elements_token/generate_token/', methods=['GET', 'POST'])
async def generate_stream_elements_token():
    return redirect("https://razbi.funcity.org/stocks-chat-minigame/streamelements_login")


    # form_data = None
    # if request.method == 'POST':
    #     form_data = await request.form
    # stream_elements_token_form = StreamElementsTokenForm(form_data)
    # if request.method == 'POST':
    #     if stream_elements_token_form.validate():
    #         # stream_elements_token = StreamElementsTokenForm.token.data
    #         session = database.Session()
    #         stream_elements_token_db = session.query(database.Settings).get('stream_elements_key')
    #         if stream_elements_token_db:
    #             stream_elements_token_db.value = stream_elements_token_form.token.data
    #         else:
    #             session.add(database.Settings(key='stream_elements_key', value=stream_elements_token_form.token.data))
    #         session.commit()
    #         app.overlord.api.stream_elements_key = stream_elements_token_form.token.data
    #         await flash("StreamElements token saved successfully.")
    #
    # return await render_template('generate_stream_elements_token.html', stream_elements_form=stream_elements_token_form,
    #                              stream_elements_token=app.overlord.api.stream_elements_key)


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
    intro = escape_word(intro, 'budget')
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
                                            'autoinvest': '#31e05a',
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
            res = escape_word(res, 'company')
            res = escape_word(res, 'amount')
            res = escape_word(res, 'budget')
            app.overlord.api.console_buffer_done = app.overlord.api.console_buffer.copy()
            await websocket.send(res)
        else:
            await asyncio.sleep(.5)


@app.websocket('/streamlabs')
async def streamlabs_ws():
    while True:
        await app.overlord.api.streamlabs_local_send_buffer_event.wait()
        app.overlord.api.streamlabs_local_send_buffer_event.clear()
        message_to_send = app.overlord.api.streamlabs_local_send_buffer
        await websocket.send(message_to_send)
        # print(f'sent: {message_to_send}')
        data = await websocket.receive()
        # print(f'received: {data}')
        app.overlord.api.streamlabs_local_receive_buffer = data
        app.overlord.api.streamlabs_local_receive_buffer_event.set()


def get_choices_for_command_names():
    pre_made_choices = []
    # print(app.overlord.api.command_names.inverse.items())
    for (og_name, alias_and_group_name) in app.overlord.api.command_names.inverse.items():
        for alias, group_name in alias_and_group_name:
            accessible_from = group_name
            if ' ' in og_name.strip():  # added this check to handle situations where the key is 'my points' so it's accessible from 'root'
                group_name, _, og_name = og_name.partition(" ")
            pre_made_choices.append({'command': (og_name, group_name), 'alias': alias, 'group': accessible_from})
    return pre_made_choices


@app.route('/customizations/command_names', methods=['GET', 'POST'])
async def command_names():
    form_data = await get_form_data()

    # pre_made_choices = [{'command': ('buy', None), 'alias': 'acquire', 'group': 'all'}]

    form_list = CommandNamesForm(form_data, data={'items': get_choices_for_command_names()})

    if request.method == 'POST':
        if "add_field" in form_data:
            field_path = form_data.get("add_field").split("-")
            field = getattr_chain(form_list, field_path)
            if field is not None:
                field.append_entry()
        elif "delete_field" in form_data:
            *field_path, field_num = form_data.get("delete_field").split("-")
            field = getattr_chain(form_list, field_path)
            if field is not None:
                field.entries = [
                    entry
                    for entry in field.entries
                    if not entry.id.endswith(f"-{field_num}")
                ]
        else:
            if form_list.validate():
                res = {}
                for result in form_list.items.data:
                    if result['alias'].lower() == 'none':
                        continue
                    result['command'] = ast.literal_eval(result['command'])
                    if result['group'] == 'None':
                        result['group'] = None
                    if result['command'][1] is not None and result['group'] is None:
                        result['command'] = (f'{result["command"][1]} {result["command"][0]}', result['command'][1])
                    res[(result['alias'], result['group'])] = result['command'][0]
                    # print(f"Added {result} to new thingies")
                app.overlord.api.command_names = BidirectionalMap(res)
                session = database.Session()
                session.query(database.Settings).get("command_names").value = repr(app.overlord.api.command_names)
                session.commit()
                # print(f"New command_names: {res}")

                form_list = CommandNamesForm(data={'items': get_choices_for_command_names()})
                await flash("Command Aliases saved successfully.")

    return await render_template('command_names.html', form_list=form_list)


@app.route('/customizations/command_names/add_alias')
async def add_alias():
    anti_duplication_count = 1
    while (f'buy{anti_duplication_count}', None) in app.overlord.api.command_names:
        anti_duplication_count += 1
        # print(f"buy{anti_duplication_count}  in command_names")
    else:
        app.overlord.api.command_names[(f'buy{anti_duplication_count}', None)] = 'buy'
        session = database.Session()
        session.query(database.Settings).get('command_names').value = repr(app.overlord.api.command_names)
        session.commit()
        # print("Added another command_name")
    return redirect('/customizations/command_names')


@app.route('/customizations/command_names/restore_default/confirmed')
async def confirm_restore_default_command_names():
    app.overlord.api.command_names = load_command_names()
    session = database.Session()
    session.query(database.Settings).get('command_names').value = repr(app.overlord.api.command_names)
    session.commit()
    await flash("Command Aliases were reset.")
    return redirect('/customizations/command_names')


@app.route('/customizations/command_names/restore_default')
async def ask_to_restore_default_command_names():
    return await render_template('command_names_restore_default.html')


@app.route('/customizations')
async def customizations():
    return await render_template('customizations.html')


@app.route('/customizations/messages', methods=['GET', 'POST'])
async def command_messages():
    # form_list = CommandMessagesForm(data={"items": [{"message_name": "thing", 'command_message': "reee"},
    #                                                 {'message_name': 'thingy2', 'command_message': 'acquire'}]})
    form_data = await get_form_data()

    messages = []
    for key, value in app.overlord.messages.items():
        messages.append({'message_name': key, "command_message": value})
    form_list = CommandMessagesForm(form_data, data={"items": messages})

    if request.method == 'POST' and form_list.validate():
        new_messages = {}
        for res in form_list.items.data:
            new_messages[res['message_name']] = res['command_message']
        app.overlord.messages = new_messages
        session = database.Session()
        session.query(database.Settings).get('messages').value = json.dumps(app.overlord.messages)
        session.commit()
        await flash("Command Outputs saved successfully.")

    return await render_template('command_messages.html', form_list=form_list)


@app.route('/customizations/messages/restore_default', methods=['GET', 'POST'])
async def command_messages_restore_default():
    form_data = await get_form_data()

    form = CommandMessagesRestoreDefaultForm(form_data)

    if request.method == 'POST':
        data = form.message_name.data
        default_messages = load_message_templates()
        if data == 'None':
            pass
        elif data == 'all':
            app.overlord.messages = default_messages
            session = database.Session()
            session.query(database.Settings).get('messages').value = json.dumps(default_messages)
            session.commit()
            await flash("Command Outputs were reset.")
        else:
            app.overlord.messages[data] = default_messages[data]
            session = database.Session()
            session.query(database.Settings).get('messages').value = json.dumps(app.overlord.messages)
            session.commit()
            await flash(f"Command Output '{data}' was reset.")
        return redirect('/customizations/messages')

    return await render_template('command_messages_restore_default.html', form=form)


@app.route('/customizations/announcements', methods=['GET', 'POST'])
async def announcements():
    form_data = await get_form_data()

    # form_list = AnnouncementForm(form_data, data={'element_list': [{'name': 'thing', 'contents': 'thingy', 'randomize_from': True}], 'result': '{thing}'})
    form_list = AnnouncementForm(form_data, data=app.overlord.announcements)

    if request.method == 'POST':
        if "add_field" in form_data:
            field_path = form_data.get("add_field").split("-")
            field = getattr_chain(form_list, field_path)
            if field is not None:
                field.append_entry()
        elif "delete_field" in form_data:
            *field_path, field_num = form_data.get("delete_field").split("-")
            field = getattr_chain(form_list, field_path)
            if field is not None:
                field.entries = [
                    entry
                    for entry in field.entries
                    if not entry.id.endswith(f"-{field_num}")
                ]
        else:
            formatter = AnnouncementDict.from_list(form_list.element_list.data)
            result = Announcement(form_list.result.data)
            try:
                formatter.validate(result)
            except ValueError as e:
                form_list.element_list.errors = [e]
                # print(form_list.element_list.errors, e)
            else:
                # print(str(result).format_map(formatter))
                announcements_saved = {'element_list': form_list.element_list.data, 'result': form_list.result.data}
                session = database.Session()
                session.query(database.Settings).get('announcements').value = repr(announcements_saved)
                session.commit()
                app.overlord.announcements = announcements_saved
                await flash("Announcements saved successfully.")

    return await render_template('announcements.html', form_list=form_list)


@app.route('/customizations/announcements/restore_default/confirmed')
async def announcements_restore_default_confirm():
    announcements_saved = load_announcements()
    session = database.Session()
    session.query(database.Settings).get('announcements').value = repr(announcements_saved)
    session.commit()
    app.overlord.announcements = announcements_saved
    await flash("Announcements reset successfully.")
    return redirect('/customizations/announcements')


@app.route('/customizations/announcements_restore_default')
async def announcements_restore_default():
    return await render_template('announcements_restore_default.html')






