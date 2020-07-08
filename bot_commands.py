import math

from API import API

from database import Company
import database


def register_commands(api: API):
    company = api.group(name="company")
    my = api.group(name="my")

    @api.command(usage="<company> <amount>")
    def buy(ctx, company: Company, amount: int):
        points = ctx.user.points(ctx.api)
        cost = math.ceil(amount*company.stock_price)

        if amount > company.remaining_shares:
            ctx.api.send_chat_message(f"@{ctx.user.name} tried buying {amount} stocks, but only {company.remaining_shares} are remaining")
            return
        if points >= cost:
            ctx.api.send_chat_message(f"@{ctx.user.name} just bought {amount} {company.abbv} for {cost} {ctx.api.overlord.currency_name}")
            share = ctx.session.query(database.Shares).filter_by(user_id=ctx.user.id, company_id=company.id).first()
            if share:
                share.amount += amount
            else:
                ctx.session.add(database.Shares(user_id=ctx.user.id, company_id=company.id, amount=amount))
            company.increase_chance += .15 * amount
            ctx.session.commit()
            ctx.api.upgraded_subtract_points(ctx.user, cost, ctx.session)
        else:
            ctx.api.send_chat_message(f"@{ctx.user.name} has {points} {ctx.api.overlord.currency_name} and requires {cost} aka {cost-points} more")

    @api.command(usage="<company> <amount>")
    def sell(ctx, company: Company, amount: int):
        cost = math.ceil(amount*company.stock_price)
        share = ctx.session.query(database.Shares).get((ctx.user.id, company.id))
        if share and share.amount >= amount:
            ctx.api.upgraded_subtract_points(ctx.user, -cost, ctx.session)
            share.amount -= amount
            if share.amount == 0:
                ctx.session.delete(share)
            company.increase_chance -= .15 * amount
            ctx.session.commit()
            ctx.api.send_chat_message(f"@{ctx.user.name} has sold {amount} stocks for {cost} {ctx.api.overlord.currency_name}")
        else:
            message = f"@{ctx.user.name} doesn't have {amount} stocks at company {company.abbv} to sell it. "
            if share:
                message += f"They require {amount-share.amount} more"
            ctx.api.send_chat_message(message)

    @api.command(usage="<company>")
    def sell_all(ctx, company: Company):
        share = ctx.session.query(database.Shares).get((ctx.user.id, company.id))
        if share:
            cost = math.ceil(share.amount*company.stock_price)
            ctx.api.upgraded_subtract_points(ctx.user, -cost, ctx.session)
            company = ctx.sssion.query(Company).get(share.company_id)
            company.increase_chance -= .15 * share.amount
            ctx.api.send_chat_message(
                f"@{ctx.user.name} has sold {share.amount} stocks for {cost} {ctx.api.overlord.currency_name}")
            ctx.session.delete(share)
            ctx.session.commit()
        else:
            ctx.api.send_chat_message(f"@{ctx.user.name} tried to sell all stocks from {company.abbv}, but they don't own any")

    @api.command(usage="<company>")
    def buy_all(ctx, company: Company):
        amount = company.remaining_shares
        points = ctx.user.points(ctx.api)
        cost = math.ceil(amount*company.stock_price)
        if amount == 0:
            ctx.api.send_chat_message(f"@{ctx.user.name} tried to buy all stocks from {company.abbv}, but there are none remaining")
            return

        if points >= cost:
            ctx.api.send_chat_message(f"@{ctx.user.name} just bought {amount} {company.abbv} for {cost} {ctx.api.overlord.currency_name}")
            share = ctx.session.query(database.Shares).filter_by(user_id=ctx.user.id, company_id=company.id).first()
            if share:
                share.amount += amount
            else:
                ctx.session.add(database.Shares(user_id=ctx.user.id, company_id=company.id, amount=amount))
            company.increase_chance += .15 * amount
            ctx.session.commit()
            ctx.api.upgraded_subtract_points(ctx.user, cost, ctx.session)
        else:
            ctx.api.send_chat_message(f"@{ctx.user.name} has {points} {ctx.api.overlord.currency_name} and requires {cost} aka {cost-points} more")

    @company.command(usage="<company>")
    def info(ctx, company: Company):
        ctx.api.send_chat_message(company)

    @company.command()
    def all(ctx):
        res = []
        companies = ctx.session.query(database.Company).all()
        for company in companies:
            # message = f"{company.abbv.upper()}[{company.stock_price-company.price_diff:.1f}{company.price_diff:+}]"
            # message = f"{company.abbv.upper()}[{company.stock_price:.1f}{company.price_diff/company.stock_price*100:+.1f}%]"
            message = company.announcement_description
            res.append(message)
        ctx.api.send_chat_message(", ".join(res))

    @company.command(usage="<company>")
    def shares(ctx, company: Company):
        ctx.api.send_chat_message(company.remaining_shares)

    @api.command()
    def stocks(ctx):
        ctx.api.send_chat_message(f"Available stocks-related chat commands: {', '.join(ctx.api.commands)}")

    @api.command()
    def info_minigame(ctx):
        ctx.api.send_chat_message("This is a stock simulation minigame made by Razbi and Nesami. "
                                  "Each 30 min equals to a month in-game. For a more in-depth explanation, please go to "
                                  "https://github.com/TheRealRazbi/Stocks-of-Razbia/blob/master/explanation.txt")

    @my.command()
    def shares(ctx):
        res = []
        shares = ctx.session.query(database.Shares).filter_by(user_id=ctx.user.id).all()
        if shares:
            for share in shares:
                company = ctx.session.query(Company).get(share.company_id).announcement_description
                res.append(f"{company}: {share.amount}")

            ctx.api.send_chat_message(", ".join(res))
        else:
            ctx.api.send_chat_message(f"@{ctx.user.name} doesn't own any shares.")

    @my.command()
    def points(ctx):
        ctx.api.send_chat_message(f"@{ctx.user.name} currently has {ctx.user.points(ctx.api)} {ctx.api.overlord.currency_name}")

    @my.command()
    def profit(ctx):
        profit_str = ctx.user.profit_str
        profit = f"@{ctx.user.name} Profit: {profit_str[0]} Profit Percentage: {profit_str[1]}"
        ctx.api.send_chat_message(profit)
    # @api.command()
    # def test_turtle(ctx, thing: str):
    #     message = ""
    #     for i in range(100):
    #         message += "thing"
    #
    #     ctx.api.send_chat_message(message)


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

