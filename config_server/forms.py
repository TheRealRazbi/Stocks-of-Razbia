from wtforms import Form, fields as f, validators as v
from wtforms_components import SelectField
import commands
from quart import current_app


class MySelectField(SelectField):
    def pre_validate(self, form):
        pass


class UsernameForm(Form):
    username = f.StringField('Username', [v.Length(min=5)], default='test')
    password = f.StringField('Password', [v.Length(min=5)], default='default_password')


class SettingForm(Form):
    value = f.StringField('value')


class CurrencyNameForm(Form):
    value = f.StringField('value', [v.Length(min=4)])


class CompanyName(Form):
    company_name = f.StringField(
        "Company name",
        [v.Length(min=5)]
    )
    abbv = f.StringField(
        "Abbreviation",
        [v.Length(min=2, max=6)],
    )


class SetupForm(Form):
    currency_system = f.SelectField('Currency System', choices=[
                                                              ('', 'Please pick a currency system'),
                                                              ('streamlabs', 'Streamlabs Extension'),
                                                              ('stream_elements', 'Stream Elements'),
                                                              ('streamlabs_local', 'Streamlabs Chatbot Local'),
                                                              ]
                                    )
    currency_name = f.StringField('Currency Name', [v.Length(min=4)])


class StreamElementsTokenForm(Form):
    token = f.StringField('token', validators=[v.Length(min=40)])


class CompaniesNames(Form):
    items = f.FieldList(f.FormField(CompanyName), min_entries=15)


def generate_choice_for_command():
    res = {'root': []}
    for command_name, command in current_app.overlord.api.commands.items():
        # if isinstance(command, commands.Command):
        res['root'].append(((command_name, None), command_name))
        if isinstance(command, commands.Group):
            res[command_name] = []
            for sub_command in command.sub_commands:
                res[command_name].append(((sub_command, command_name), sub_command))
    return res.items()


def generate_choice_for_group():
    res = [(None, 'root')]
    for command_name, command in current_app.overlord.api.commands.items():
        if isinstance(command, commands.Group):
            res.append((command_name, command_name))
    return res


# ('first', (('First', 'Maybe First'), )), # this is an example of how to structure groups
# ('second', (('Second', 'Maybe Second'), ))
class CommandNameForm(Form):
    alias = f.StringField(
        "Alias",
        [v.Length(min=2), v.InputRequired()]
    )
    command = MySelectField('Command', choices=generate_choice_for_command)

    group = MySelectField('Accessible from group', choices=generate_choice_for_group)


class CommandNamesForm(Form):
    items = f.FieldList(f.FormField(CommandNameForm))


class CommandMessageForm(Form):
    message_name = f.TextAreaField("Message ID", render_kw={'rows': 3, 'readonly': True})
    command_message = f.TextAreaField("Command Output",
                                      validators=[v.Length(min=3)],
                                      render_kw={'rows': 3, 'cols': 1})


class CommandMessagesForm(Form):
    items = f.FieldList(f.FormField(CommandMessageForm))


def generate_choice_for_message_name():
    # noinspection PyTypeChecker
    return [(None, 'Please pick a command to restore to default')] +\
           [(key, key) for key in current_app.overlord.messages] +\
           [('all', 'literally all of them')]


class CommandMessagesRestoreDefaultForm(Form):
    message_name = MySelectField('Announcement Name', choices=generate_choice_for_message_name)


class AnnouncementElementForm(Form):
    name = f.TextAreaField('name', validators=[v.InputRequired()])
    contents = f.TextAreaField('content', render_kw={'rows': 3}, validators=[v.InputRequired()])
    randomize_from = f.BooleanField('randomize_from', default=False)


class AnnouncementForm(Form):
    element_list = f.FieldList(f.FormField(AnnouncementElementForm))
    result = f.TextAreaField('announcement')









