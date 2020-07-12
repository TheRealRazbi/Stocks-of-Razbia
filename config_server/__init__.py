from quart import Quart, render_template
from database import Company, Session

app = Quart(__name__, static_folder="static/static")


@app.route('/')
async def home():
    return await render_template("home.html")


@app.route('/list_company')
async def list_companies():
    session = Session()
    companies = session.query(Company).order_by(Company.price_diff.desc()).all()
    return await render_template("companies.html", companies=companies)


@app.route('/settings')
async def settings():
    return await render_template('settings.html')



