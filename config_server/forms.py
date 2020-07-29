from wtforms import Form, BooleanField, StringField, validators, SelectField


class UsernameForm(Form):
    username = StringField('Username', [validators.Length(min=5)], default='test')
    password = StringField('Password', [validators.Length(min=5)], default='default_password')


class SettingForm(Form):
    value = StringField('value')


class CurrencyNameForm(Form):
    value = StringField('value', [validators.Length(min=4)])


class SetupForm(Form):
    currency_system = SelectField('Currency System', choices=[
                                                              ('', 'Please pick a currency system'),
                                                              ('streamlabs', 'Streamlabs Extension'),
                                                              ('stream_elements', 'Stream Elements'),
                                                              ('streamlabs_local', 'Streamlabs Local[not available yet]'),
                                                              ]
                                  )
    currency_name = StringField('Currency Name', [validators.Length(min=4)])


class StreamElementsTokenForm(Form):
    token = StringField('token', [validators.Length(min=40)])
