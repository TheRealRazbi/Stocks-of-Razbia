import math

from API import API

from database import Company
import database
from multi_arg import IntOrStrAll, CompanyOrIntOrAll
import commands as commands_
import time
import random


def register_commands(api: API):
    my = api.group(name="my")
    all = api.group(name='all')
    next = api.group(name='next')

    @all.command()
    async def commands(ctx):
        thing_to_display = []
        for command_name, command in ctx.api.commands.items():
            if isinstance(command, commands_.Command):
                thing_to_display.append(f'!{command_name}')
            else:
                thing_to_display.append(f'!{command_name}[{", ".join(command.sub_commands)}]')

        ctx.api.send_chat_message(f"All minigame-related chat commands: {', '.join(thing_to_display)}")

    @api.command(usage="<company> <amount>")
    async def buy(ctx, company: CompanyOrIntOrAll, amount: CompanyOrIntOrAll):
        if isinstance(company, Company) and not isinstance(amount, Company):
            if amount == 'all':
                amount = company.remaining_shares
        elif not isinstance(company, Company) and isinstance(amount, Company):
            company, amount = amount, company
            if amount == 'all':
                amount = company.remaining_shares
        elif isinstance(company, Company) and isinstance(amount, Company):
            ctx.api.send_chat_message(f"@{ctx.user.name} inputted 2 companies. You need to input a value and a company")
            return
        elif not isinstance(company, Company) and not isinstance(amount, Company):
            ctx.api.send_chat_message(f"@{ctx.user.name} didn't input any company. You need to input a value and a company")
            return

        points = await ctx.user.points(ctx.api)
        cost = math.ceil(amount*company.stock_price)

        if company.remaining_shares == 0:
            ctx.api.send_chat_message(f"@{ctx.user.name} no stocks left to buy at {company.abbv}")
            return
        if amount > company.remaining_shares:
            ctx.api.send_chat_message(f"@{ctx.user.name} tried buying {amount} stocks, but only {company.remaining_shares} are remaining")
            return
        if points >= cost:
            share = ctx.session.query(database.Shares).filter_by(user_id=ctx.user.id, company_id=company.id).first()
            if share:
                share.amount += amount
            else:
                share = database.Shares(user_id=ctx.user.id, company_id=company.id, amount=amount)
                ctx.session.add(share)
                # share = ctx.session.query(database.Shares).filter_by(user_id=ctx.user.id, company_id=company.id).first()
            company.increase_chance += .01 * amount
            ctx.session.commit()
            await ctx.api.upgraded_add_points(ctx.user, -cost, ctx.session)
            ctx.api.send_chat_message(f"@{ctx.user.name} just bought {amount} stocks from [{company.abbv}] '{company.full_name}' for {cost} {ctx.api.overlord.currency_name}. "
                                      f"Now they gain {math.ceil(share.amount*company.stock_price*.1)} {ctx.api.overlord.currency_name} from {company.abbv} each 10 mins. "
                                      # f"""{"Tip: Use '!my income' to check your income." if ctx.user.new else ""}"""
                                      )
            # if ctx.user.new:
            #     ctx.user.new = False
            #     ctx.session.commit()
        else:
            ctx.api.send_chat_message(f"@{ctx.user.name} has {points} {ctx.api.overlord.currency_name} and requires {cost} aka {cost-points} more")

    @api.command(usage="<company> <amount>")
    async def sell(ctx, company: CompanyOrIntOrAll, amount: CompanyOrIntOrAll):
        if isinstance(company, Company) and not isinstance(amount, Company):
            pass
        elif not isinstance(company, Company) and isinstance(amount, Company):
            company, amount = amount, company
        elif isinstance(company, Company) and isinstance(amount, Company):
            ctx.api.send_chat_message(f"@{ctx.user.name} You input 2 companies. you need to input a value and a company")
            return
        elif not isinstance(company, Company) and not isinstance(amount, Company):
            ctx.api.send_chat_message(f"@{ctx.user.name} You didn't input any company. you need to input a value and a company")
            return

        share = ctx.session.query(database.Shares).get((ctx.user.id, company.id))
        if amount == 'all' and share or share and share.amount >= amount:
            if amount == 'all':
                amount = share.amount
            cost = math.ceil(amount * company.stock_price)

            await ctx.api.upgraded_add_points(ctx.user, cost, ctx.session)
            share.amount -= amount
            if share.amount == 0:
                ctx.session.delete(share)
            company.increase_chance -= .01 * amount
            ctx.session.commit()
            ctx.api.send_chat_message(f"@{ctx.user.name} has sold {amount} stocks from [{company.abbv}] '{company.full_name}' for {cost} {ctx.api.overlord.currency_name}.")
        else:
            if not share:
                message = f"@{ctx.user.name} doesn't have any stocks at company {company.abbv}."
            else:
                message = f"@{ctx.user.name} doesn't have {amount} stocks at company {company.abbv} to sell them. "\
                          f"They have only {share.amount} stock{'s' if share.amount != 1 else ''}."
            ctx.api.send_chat_message(message)

    # @company.command(usage="<company>")
    @api.command(usage="<company>")
    async def company(ctx, company: Company):
        ctx.api.send_chat_message(company)

    @api.command()
    async def companies(ctx):
        res = []
        companies = ctx.session.query(database.Company).order_by(Company.stock_price.desc()).all()
        for company in companies:
            # message = f"{company.abbv.upper()}[{company.stock_price-company.price_diff:.1f}{company.price_diff:+}]"
            # message = f"{company.abbv.upper()}[{company.stock_price:.1f}{company.price_diff/company.stock_price*100:+.1f}%]"
            message = company.announcement_description
            res.append(message)
        ctx.api.send_chat_message(f"@{ctx.user.name} {', '.join(res)} ")
        if ctx.user.new:
            ctx.api.send_chat_message(f"@{ctx.user.name} Tip: The number on the left is the 'current price'. The one on the right is the 'price change'")
            ctx.user.new = False
            ctx.session.commit()
    # @company.command(usage="<company>")
    # async def shares(ctx, company: Company):
    #     ctx.api.send_chat_message(f"@{ctx.user.name} '{company.abbv}' has {company.remaining_shares} remaining shares")

    @api.command()
    async def stocks(ctx):
        ctx.api.send_chat_message(f"@{ctx.user.name} Minigame basic commands: !autoinvest, !introduction, !buy, !companies, !all commands, !my profit, !my income")

    @api.command()
    async def stonks(ctx):
        await stocks(ctx)

    @api.command()
    async def introduction(ctx):
        ctx.api.send_chat_message("This is a stock simulation minigame | '!stocks' for basic commands | "
                                  "Buy stocks for passive income | "
                                  "Naming Convention: Company[current_price, price_change] "
                                  # "For a more in-depth explanation, please go to "
                                  # "https://github.com/TheRealRazbi/Stocks-of-Razbia/blob/master/introduction.md"
                                  )

    @api.command()
    async def next_month(ctx):
        time_since_last_run = time.time() - ctx.api.overlord.last_check
        time_till_next_run = ctx.api.overlord.iterate_cooldown - time_since_last_run
        ctx.api.send_chat_message(f"@{ctx.user.name} The next month starts in {time_till_next_run/60:.0f} minutes")

    @my.command()
    async def shares(ctx):
        res = []
        shares = ctx.session.query(database.Shares).filter_by(user_id=ctx.user.id).all()
        if shares:
            for share in shares:
                company = ctx.session.query(Company).get(share.company_id).announcement_description
                res.append(f"{company}: {share.amount}")

            ctx.api.send_chat_message(f'@{ctx.user.name} has {", ".join(res)}')
        else:
            ctx.api.send_chat_message(f"@{ctx.user.name} doesn't own any shares. Use '!buy' to buy some.")

    @my.command()
    async def points(ctx):
        ctx.api.send_chat_message(f"@{ctx.user.name} currently has {await ctx.user.points(ctx.api)} {ctx.api.overlord.currency_name}")

    @api.command()
    async def mypoints(ctx):
        await points(ctx)

    @my.command()
    async def profit(ctx):
        profit_str = ctx.user.profit_str
        profit = f"@{ctx.user.name} Profit: {profit_str[0]} {ctx.api.overlord.currency_name} | Profit Percentage: {profit_str[1]}"
        ctx.api.send_chat_message(profit)

    @api.command()
    async def myprofit(ctx):
        await profit(ctx)

    @my.command()
    async def income(ctx):
        res = []
        shares = ctx.session.query(database.Shares).filter_by(user_id=ctx.user.id).all()
        if shares:
            total_income = 0
            for share in shares:
                company = ctx.session.query(Company).get(share.company_id)
                stock_price = company.stock_price
                total_income += math.ceil(stock_price*share.amount*.1)
                res.append(f"{company.abbv}: {math.ceil(stock_price*share.amount*.1)}")

            ctx.api.send_chat_message(f'@{ctx.user.name} {", ".join(res)} | Total: {total_income} {ctx.api.overlord.currency_name} per 10 mins.')
        else:
            ctx.api.send_chat_message(f"@{ctx.user.name} doesn't own any shares. Use '!buy' to buy some.")

    @api.command()
    async def myincome(ctx):
        await income(ctx)

    @next.command()
    async def month(ctx):
        time_since_last_run = time.time() - ctx.api.overlord.last_check
        time_till_next_run = ctx.api.overlord.iterate_cooldown - time_since_last_run
        ctx.api.send_chat_message(f"@{ctx.user.name} The next month starts in {time_till_next_run/60:.0f} minutes")

    @api.command(usage='<budget>')
    async def autoinvest(ctx, budget: int):
        user_points = await ctx.user.points(ctx.api)
        if budget <= user_points:
            companies: list = ctx.session.query(database.Company).all()
            for index_company, company in enumerate(companies):
                if company.stock_price < 3 or company.stock_price > budget or company.remaining_shares == 0:
                    companies.pop(index_company)
            chosen_company: Company = random.choice(companies)
            if chosen_company:
                stocks_to_buy = math.floor(budget/chosen_company.stock_price)
                if stocks_to_buy > chosen_company.remaining_shares:
                    stocks_to_buy = chosen_company.remaining_shares
                if stocks_to_buy <= 0:
                    ctx.api.send_chat_message(f"@{ctx.user.name} too small budget. No stocks bought.")
                    return
                await buy.run(ctx, stocks_to_buy, chosen_company)
                # share = ctx.session.query(database.Shares).get((ctx.user.id, chosen_company.id))
                # if share:
                #     share.amount += stocks_to_buy
                # else:
                #     share = database.Shares(user_id=ctx.user.id, company_id=chosen_company.id, amount=stocks_to_buy)
                #     ctx.session.add(share)
                # ctx.session.commit()
                # total_cost = math.ceil(stocks_to_buy*chosen_company.stock_price)
                # await ctx.api.add_points(ctx.user.name, -total_cost)
                # ctx.api.send_chat_message(
                #     f"@{ctx.user.name} just bought {stocks_to_buy} stocks from [{chosen_company.abbv}] '{chosen_company.full_name}' for {total_cost} {ctx.api.overlord.currency_name}. "
                #     f"Now they gain {math.ceil(share.amount * chosen_company.stock_price * .1)} {ctx.api.overlord.currency_name} from {chosen_company.abbv} each 10 mins. ")

            else:
                ctx.api.send_chat_message(f"@{ctx.user.name} too small budget. No stocks bought.")
        else:
            ctx.api.send_chat_message(f"@{ctx.user.name} you need {budget} {ctx.api.overlord.currency_name}, aka you need {budget-user_points} more.")

    @api.command()
    async def about(ctx):
        ctx.api.send_chat_message("This minigame is open-source and it was made by Razbi and Nesami. Github link: https://github.com/TheRealRazbi/Stocks-of-Razbia")


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

