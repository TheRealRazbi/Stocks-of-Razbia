import math

from API import API

from database import Company
import database


def register_commands(api: API):
    stocks = api.group(name="stocks")

    @stocks.command(usage="<amount> <company>")
    def buy(ctx, amount: int, company: Company):
        points = ctx.user.points(ctx.api)
        cost = math.ceil(amount*company.stock_price)
        if points >= cost:
            ctx.api.send_chat_message(f"@{ctx.user.name} just bought {amount} {company.abbv} for {cost} points")
            share = ctx.session.query(database.Shares).filter_by(user_id=ctx.user.id, company_id=company.id).first()
            if share:
                share.amount += amount
                ctx.session.commit()
            else:
                ctx.session.add(database.Shares(user_id=ctx.user.id, company_id=company.id, amount=amount))
                ctx.session.commit()
            ctx.api.subtract_points(ctx.user.name, cost)
        else:
            ctx.api.send_chat_message(f"@{ctx.user.name} has  {points} points and requires {cost} aka {cost-points} more")

    @stocks.command(usage="<amount> <company>")
    def sell(ctx, amount: int, company: Company):
        cost = math.ceil(amount*company.stock_price)
        share = ctx.session.query(database.Shares).get((ctx.user.id, company.id))
        if share and share.amount >= amount:
            ctx.api.subtract_points(ctx.user.name, -cost)
            share.amount -= amount
            ctx.session.commit()
            ctx.api.send_chat_message(f"@{ctx.user.name} has sold {amount} stocks for {cost} points")
        else:
            message = f"@{ctx.user.name} doesn't have {amount} stocks at company {company.abbv} to sell it. "
            if share:
                message += f"They require {amount-share.amount} more"
            ctx.api.send_chat_message(message)

    @api.command()
    def info_company(ctx, company: Company):
        ctx.api.send_chat_message(company)

    @api.command()
    def test_turtle(ctx, thing: str):
        message = ""
        for i in range(100):
            message += "thing"

        ctx.api.send_chat_message(message)


if __name__ == '__main__':
    pass
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(buy_stocks)
    # b = BuyCommand()
    # print(b.run.__annotations__)
    # buy_stocks(1, "reee")
    # api = API()
    # buy_stocks(1, '1')
    # ctx = Contdext(api, user)
    # prepared_args = prepare_args(ctx, command, args)
    # command(ctx, *args)

