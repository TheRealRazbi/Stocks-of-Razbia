from wtforms import Form, BooleanField, StringField, validators


class UsernameForm(Form):
    username = StringField('Username', [validators.Length(min=5)], default='test')
    password = StringField('Password', [validators.Length(min=5)], default='default_password')


class SettingForm(Form):
    value = StringField('value')


class CurrencyNameForm(Form):
    value = StringField('value', [validators.Length(min=4)])


