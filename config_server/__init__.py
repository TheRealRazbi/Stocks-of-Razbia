import ast
import json
import math
import time
from contextlib import suppress
from typing import Type, List, Optional

from quart import Quart, render_template, request, flash, redirect, url_for, websocket, current_app
import database
from wtforms import validators, Form, FieldList

from announcements import AnnouncementDict, Announcement
from config_server.forms import SettingForm, SetupForm, StreamElementsTokenForm, CompaniesNames, CommandNameForm, \
    CommandNamesForm, CommandMessagesForm, CommandMessagesRestoreDefaultForm, AnnouncementForm, TestCommandForm
import asyncio
import markdown2
from testing_commands import FakeOverlord
from customizable_stuff import load_command_names, load_message_templates, load_announcements
from more_tools import BidirectionalMap
import atexit

app = Quart(__name__, static_folder="static/static")
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@atexit.register
def close_web_socket_upon_crash():
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(websocket.close())
    except:
        pass


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
    session = database.Session()
    most = {
            'wealthy_user': session.query(database.User).order_by((database.User.gain-database.User.lost).desc()).first(),
            'poorest_user': session.query(database.User).order_by((database.User.gain-database.User.lost)).first(),
            'richest_company': session.query(database.Company).order_by(database.Company.stock_price.desc()).first(),
            'most_bought_company': session.query(database.Company).order_by(database.Company.stocks_bought.desc()).first(),
            'oldest_company': session.query(database.Company).order_by(database.Company.months.desc()).first()
            }

    return await render_template("home.html", tokens_loaded=app.overlord.api.tokens_ready, started=app.overlord.started,
                                 currency_system=app.overlord.api.currency_system.capitalize(), currency_name=app.overlord.currency_name,
                                 most=most, round=round, int=int)


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
    intro = intro.replace("Basic Commands:", """
    <div class="accordion my-accordion" id="accordionExample">
        <div class="card">
            <div class="card-header" id="headingOne">
              <h5 class="mb-0">
                <button class="btn btn-link" type="button" data-toggle="collapse" data-target="#collapseOne" aria-expanded="true" aria-controls="collapseOne">
                  Basic Commands
                </button>
              </h5>
    </div>
    <div id="collapseOne" class="collapse" aria-labelledby="headingOne" data-parent="#accordionExample">
      <div class="card-body">
    """)
    intro = intro.replace("Extra Commands:", """
    </div></div></div>
      <div class="card">
    <div class="card-header" id="headingTwo">
      <h5 class="mb-0">
        <button class="btn btn-link collapsed" type="button" data-toggle="collapse" data-target="#collapseTwo" aria-expanded="false" aria-controls="collapseTwo">
          Extra Commands
        </button>
      </h5>
    </div>
    <div id="collapseTwo" class="collapse" aria-labelledby="headingTwo" data-parent="#accordionExample">
      <div class="card-body">
    """)
    intro = intro.replace("Event System:", """
    </div></div></div>
      <div class="card">
    <div class="card-header" id="headingThree">
      <h5 class="mb-0">
        <button class="btn btn-link collapsed" type="button" data-toggle="collapse" data-target="#collapseThree" aria-expanded="false" aria-controls="collapseThree">
        Event System:
    </button>
      </h5>
    </div>
    <div id="collapseThree" class="collapse" aria-labelledby="headingThree" data-parent="#accordionExample">
      <div class="card-body">
    """)
    intro = intro.replace("TL;DR:", """
        </div></div></div>
        <div class="card">
            <div class="card-header" id="headingFour">
              <h5 class="mb-0">
                <button class="btn btn-link collapsed" type="button" data-toggle="collapse" data-target="#collapseFour" aria-expanded="false" aria-controls="collapseFour">
                TL;DR
            </button>
              </h5>
            </div>
        <div id="collapseFour" class="collapse" aria-labelledby="headingFour" data-parent="#accordionExample">
          <div class="card-body">

""")
    intro = intro.replace("The minigame and all", """
    </div></div></div><br>The minigame and all
    """)
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
    for (og_name, alias_and_group_name) in app.overlord.api.command_names.inverse.items():
        for alias, group_name in alias_and_group_name:
            temp_og_name = og_name
            accessible_from = group_name
            if ' ' in og_name.strip():  # added this check to handle situations where the key is 'my points' so it's accessible from 'root'
                group_name, _, temp_og_name = og_name.partition(" ")
            pre_made_choices.append({'command': (temp_og_name, group_name), 'alias': alias, 'group': accessible_from})
    return pre_made_choices


@app.route('/customizations/command_names', methods=['GET', 'POST'])
async def command_names():
    form_data = await get_form_data()
    # pre_made_choices = [{'command': ('buy', None), 'alias': 'acquire', 'group': 'all'}]
    form_list = CommandNamesForm(form_data, data={'items': get_choices_for_command_names()})
    test_command_form = TestCommandForm(form_data, data={'user_points': 10000})

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
                default_command_names = load_command_names()
                saved_result = {}
                for key in res:
                    if key in default_command_names:
                        if res[key] != default_command_names[key]:
                            saved_result[key] = res[key]
                    else:
                        saved_result[key] = res[key]
                # print(f"\ndefault: {default_command_names}\nres: {res}\ncurrent_command_names: {app.overlord.api.command_names}\nsaved_result: {saved_result}")

                session = database.Session()
                if command_names_db := session.query(database.Settings).get("command_names"):
                    command_names_db.value = repr(saved_result)
                else:
                    session.add(database.Settings(key='command_names', value=repr(saved_result)))
                session.commit()
                # print(f"New command_names: {res}")

                form_list = CommandNamesForm(data={'items': get_choices_for_command_names()})
                await flash("Command Aliases saved successfully.")

    return await render_template('command_names.html', form_list=form_list, test_command_form=test_command_form)


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
    if command_names_db := session.query(database.Settings).get('command_names'):
        session.delete(command_names_db)
    session.commit()
    await flash("Command Aliases were reset.")
    return redirect('/customizations/command_names')


@app.route('/customizations/command_names/restore_default')
async def ask_to_restore_default_command_names():
    first_option = '/customizations/command_names/restore_default/confirmed'
    second_option = '/customizations/command_names'
    warning_message = '<b>reset</b> all command aliases'
    return await render_template('are_you_sure_template.html', first_option=first_option, second_option=second_option,
                                 warning_message=warning_message)


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
    test_command_form = TestCommandForm(form_data, data={'user_points': 10000})

    if request.method == 'POST':
        if form_list.validate():
            new_messages = {}
            saved_messages = {}
            default_messages = load_message_templates()
            for res in form_list.items.data:
                new_messages[res['message_name']] = res['command_message']
                if res['message_name'] in default_messages:
                    if res['command_message'] != default_messages[res['message_name']]:
                        print(f"Saved {res['command_message']} because: {res['command_message']} is different than {default_messages[res['message_name']]}")
                        saved_messages[res['message_name']] = res['command_message']
            app.overlord.messages = new_messages
            session = database.Session()
            # session.query(database.Settings).get('messages').value = json.dumps(app.overlord.messages)
            if messages_db := session.query(database.Settings).get('messages'):
                messages_db.value = json.dumps(saved_messages)
            else:
                session.add(database.Settings(key='messages', value=json.dumps(saved_messages)))
            session.commit()
            await flash("Command Outputs saved successfully.")

    return await render_template('command_messages.html', form_list=form_list, test_command_form=test_command_form)


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
            if messages_db := session.query(database.Settings).get('messages'):
                session.delete(messages_db)
            session.commit()
            await flash("Command Outputs were reset.")
        else:
            app.overlord.messages[data] = default_messages[data]
            session = database.Session()
            if messages_db := session.query(database.Settings).get('messages'):
                data_from_db = json.loads(messages_db.value)
                new_messages = {}
                for message_name in data_from_db:
                    if not message_name == data:
                        new_messages[message_name] = default_messages[message_name]
                messages_db.value = json.dumps(new_messages)
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
                default_announcements = load_announcements()
                announcements_saved = {'element_list': form_list.element_list.data, 'result': form_list.result.data}
                session = database.Session()
                if announcements_db := session.query(database.Settings).get('announcements'):
                    if announcements_saved != default_announcements:
                        announcements_db.value = repr(announcements_saved)
                elif not announcements_db and announcements_saved != default_announcements:
                    session.add(database.Settings(key='announcements', value=repr(announcements_saved)))

                session.commit()
                app.overlord.announcements = announcements_saved
                await flash("Announcements saved successfully.")

    return await render_template('announcements.html', form_list=form_list, str=str, Announcement=Announcement, AnnouncementDict=AnnouncementDict)


@app.route('/customizations/announcements/restore_default/confirmed')
async def announcements_restore_default_confirm():
    session = database.Session()
    if announcements_db := session.query(database.Settings).get('announcements'):
        session.delete(announcements_db)
    session.commit()
    announcements_saved = load_announcements()
    app.overlord.announcements = announcements_saved
    await flash("Announcements reset successfully.")
    return redirect('/customizations/announcements')


@app.route('/customizations/announcements/restore_default')
async def announcements_restore_default():
    first_option = "/customizations/announcements/restore_default/confirmed"
    second_option = '/customizations/announcements'
    warning_message = "<b>reset</b> announcements to default"
    return await render_template('are_you_sure_template.html', first_option=first_option, second_option=second_option,
                                 warning_message=warning_message)


@app.route('/customizations/announcements/test', methods=['POST'])
async def announcements_test():
    form_data = await get_form_data()
    form_list = AnnouncementForm(form_data, data=app.overlord.announcements)
    formatter = AnnouncementDict.from_list(form_list.element_list.data)
    result = Announcement(form_list.result.data)
    try:
        formatter.validate(result)
    except ValueError as e:
        return f'Error: {e}'
    return str(result).format_map(formatter).replace("[currency_name]", app.overlord.currency_name)


@app.route('/customizations/company_names/restore_default')
async def company_names_restore_default():
    first_option = '/customizations/company_names/restore_default/confirmed'
    second_option = '/customizations/company_names'
    warning_message = '<b>reset</b> company names to default'
    return await render_template('are_you_sure_template.html', first_option=first_option, second_option=second_option,
                                 warning_message=warning_message)


@app.route('/customizations/company_names/restore_default/confirmed')
async def company_names_restore_default_confirm():
    session = database.Session()
    session.delete(session.query(database.Settings).get('company_names'))
    app.overlord.load_names(session)
    session.commit()
    await flash("Company Names reset successfully.")
    return redirect('/customizations/company_names')


@app.route('/customizations/company_names/reset')
async def company_names_reset():
    first_option = '/customizations/company_names/reset/confirm'
    second_option = '/customizations/company_names'
    warning_message = "<b>refund</b> all stocks and <b>delete</b> current companies"
    return await render_template('are_you_sure_template.html', first_option=first_option, second_option=second_option,
                                 warning_message=warning_message
                                 )


@app.route('/customizations/company_names/reset/confirm')
async def company_names_reset_confirm():
    session = database.Session()
    for share in session.query(database.Shares).all():
        await app.overlord.api.upgraded_add_points(share.user, math.ceil(share.amount*share.company.stock_price), session)
        session.delete(share)
    session.query(database.Company).delete()
    session.commit()
    await flash("Refunded all stocks. Deleted current companies.")
    return redirect('/customizations/company_names')


@app.route('/test/test')
async def testing_bootstrap_features():
    return await render_template('testing_bootstrap_features.html')


@app.route('/customizations/testing_commands', methods=['POST'])
async def testing_commands():
    form_data = await get_form_data()
    # print(form_data)
    form = TestCommandForm(form_data, data={'user_points': 10000})

    form_messages = CommandMessagesForm(form_data)
    new_messages = {}
    if form_messages.validate():
        for res in form_messages.items.data:
            new_messages[res['message_name']] = res['command_message']
    if new_messages == {}:
        new_messages = app.overlord.messages

    form_names = CommandNamesForm(form_data, data={'items': get_choices_for_command_names()})
    command_names = {}
    for result in form_names.items.data:
        if result['alias'].lower() == 'none' or result['command'] is None:
            continue
        result['command'] = ast.literal_eval(result['command'])
        if result['group'] == 'None':
            result['group'] = None
        if result['command'][1] is not None and result['group'] is None:
            result['command'] = (f'{result["command"][1]} {result["command"][0]}', result['command'][1])
        command_names[(result['alias'], result['group'])] = result['command'][0]
    if command_names == {}:
        command_names = app.overlord.api.command_names

    fake_overlord = FakeOverlord(messages_dict=new_messages, command_names=command_names,
                                 name=app.overlord.api.name, currency_name=app.overlord.currency_name,
                                 user_points=form.user_points.data)
    # print(form.contents.data)
    await fake_overlord.api.handler(form.contents.data)
    # print(fake_overlord.api.message_sent_buffer)
    res = '\n'.join(fake_overlord.return_sent_messages())
    if res == '':
        res = "*No output*"
    return {'message': res, 'user_points': fake_overlord.api.fake_points}







