from wtforms import Form, fields as f, validators as v


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
        [v.Length(min=3, max=6)],
    )


class SetupForm(Form):
    currency_system = f.SelectField(
        'Currency System',
        choices=[
            ('', 'Please pick a currency system'),
            ('streamlabs', 'Streamlabs Extension'),
            ('stream_elements', 'Stream Elements'),
            ('streamlabs_local', 'Streamlabs Local[not available yet]'),
        ]
    )
    currency_name = f.StringField('Currency Name', validators=[v.Length(min=4)])


class StreamElementsTokenForm(Form):
    token = f.StringField('token', validators=[v.Length(min=40)])


class CompaniesNames(Form):
    items = f.FieldList(f.FormField(CompanyName), min_entries=15)
