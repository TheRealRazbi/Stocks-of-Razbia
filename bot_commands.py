import math

from sqlalchemy import func

from API import API

from database import Company
import database as db
from multi_arg import IntOrStrAll, CompanyOrIntOrAll, CompanyOrInt
import commands as commands_
import time
import random
from typing import Union


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
        amount: Union[Company, int, 'all']
        company: Union[Company, int, 'all']
        if isinstance(company, Company) and not isinstance(amount, Company):
            pass
        elif not isinstance(company, Company) and isinstance(amount, Company):
            company, amount = amount, company
        elif isinstance(company, Company) and isinstance(amount, Company):
            # ctx.api.send_chat_message(f"@{ctx.user.name} inputted 2 companies. You need to input a number and a company.")
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'buy_or_sell_2_companies'))
            return
        elif not isinstance(company, Company) and not isinstance(amount, Company):
            # ctx.api.send_chat_message(f"@{ctx.user.name} didn't input any company. You need to input a number and a company.")
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'buy_or_sell_0_companies'))
            return

        points = await ctx.user.points(ctx.api)
        if amount == 'all':
            amount = math.floor(points/company.stock_price)

        if share := ctx.session.query(db.Shares).get((ctx.user.id, company.id)):
            stocks_till_100k = 100_000 - share.amount
            if stocks_till_100k == 0:
                ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'reached_stocks_limit', company_abbv=company.abbv))
                return
            amount = min(amount, stocks_till_100k)
        else:
            amount = min(amount, 100_000)

        if amount <= 0:
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'number_too_small'))
            return

        cost = math.ceil(amount*company.stock_price)
        # if company.remaining_shares == 0:
        #     ctx.api.send_chat_message(f"@{ctx.user.name} no stocks left to buy at {company.abbv}")
        #     return
        # if amount > company.remaining_shares:
        #     ctx.api.send_chat_message(f"@{ctx.user.name} tried buying {amount} stocks, but only {company.remaining_shares} are remaining")
        #     return
        if points >= cost:
            if share:
                share.amount += amount
            else:
                share = db.Shares(user_id=ctx.user.id, company_id=company.id, amount=amount)
                ctx.session.add(share)
            company.increase_chance = 50 + .01 * company.stocks_bought
            if company.increase_chance > 55:
                company.increase_chance = 55
            ctx.session.commit()
            await ctx.api.upgraded_add_points(ctx.user, -cost, ctx.session)
            # ctx.api.send_chat_message(f"@{ctx.user.name} just bought {amount} stocks from [{company.abbv}] '{company.full_name}' for {cost} {ctx.api.overlord.currency_name}. "
            #                           f"Now they gain {math.ceil(share.amount*company.stock_price*.1)} {ctx.api.overlord.currency_name} from {company.abbv} each 10 mins. ")
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'buy_successful',
                                                             amount=f'{amount:,}',
                                                             company_abbv=company.abbv,
                                                             company_full_name=company.full_name,
                                                             cost=f'{cost:,}',
                                                             passive_income=f'{ctx.user.passive_income(company, ctx.session):,}'))

            # if ctx.user.new:
            #     ctx.user.new = False
            #     ctx.session.commit()
        else:
            # ctx.api.send_chat_message(f"@{ctx.user.name} has {points:,} {ctx.api.overlord.currency_name} and requires {cost} aka {cost-points} more.")
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'buy_not_enough_points',
                                                             points=f'{points:,}',
                                                             cost=f'{cost:,}',
                                                             cost_minus_points=f'{cost-points:,}'))

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

        share = ctx.session.query(db.Shares).get((ctx.user.id, company.id))
        if amount == 'all' and share or share and share.amount >= amount:
            if amount == 'all':
                amount = share.amount
            if amount <= 0:
                ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'number_too_small'))
                return
            cost = math.ceil(amount * company.stock_price)

            await ctx.api.upgraded_add_points(ctx.user, cost, ctx.session)
            share.amount -= amount
            if share.amount == 0:
                ctx.session.delete(share)
            company.increase_chance = 50 + .01 * company.stocks_bought
            if company.increase_chance > 55:
                company.increase_chance = 55
            ctx.session.commit()
            # ctx.api.send_chat_message(f"@{ctx.user.name} has sold {amount} stocks from [{company.abbv}] '{company.full_name}' for {cost} {ctx.api.overlord.currency_name}.")
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'sell_successful',
                                                             amount=f'{amount:,}',
                                                             company_abbv=company.abbv,
                                                             company_full_name=company.full_name,
                                                             cost=f'{cost:,}'))
        else:
            if not share:
                # message = f"@{ctx.user.name} doesn't have any stocks at company {company.abbv}."
                message = ctx.api.get_and_format(ctx, 'sell_no_shares',
                                                 company_abbv=company.abbv)
            else:
                # message = f"@{ctx.user.name} doesn't have {amount} stocks at company {company.abbv} to sell them. "\
                #           f"They have only {share.amount} stock{'s' if share.amount != 1 else ''}."
                message = ctx.api.get_and_format(ctx, 'sell_not_enough_shares',
                                                 company_abbv=company.abbv,
                                                 share_amount=f'{share.amount:,}')
            ctx.api.send_chat_message(message)

    @api.command()
    async def sell_everything(ctx):
        total_outcome = 0
        list_of_all_sells = []
        if not len(ctx.user.shares):
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'no_shares'))
            return
        for share in ctx.user.shares:
            company = share.company
            total_outcome += math.ceil(share.amount*company.stock_price)
            list_of_all_sells.append(f'{company.abbv}: {share.amount:,}')
            ctx.session.delete(share)
        await ctx.api.upgraded_add_points(ctx.user, total_outcome, ctx.session)
        ctx.session.commit()
        list_of_all_sells = ", ".join(list_of_all_sells)
        ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'sell_everything_successful',
                                                         list_of_all_sells=list_of_all_sells,
                                                         total_outcome=f'{total_outcome:,}'))

    @api.command(usage="<company>")
    async def company(ctx, company: Company):
        ctx.api.send_chat_message(company)

    @api.command()
    async def companies(ctx):
        res = []
        companies = ctx.session.query(db.Company).order_by(Company.stock_price.desc()).all()
        for company in companies:
            # message = f"{company.abbv.upper()}[{company.stock_price-company.price_diff:.1f}{company.price_diff:+}]"
            # message = f"{company.abbv.upper()}[{company.stock_price:.1f}{company.price_diff/company.stock_price*100:+.1f}%]"
            message = company.announcement_description
            res.append(message)
        if ctx.user.new:
            # ctx.api.send_chat_message(f"@{ctx.user.name} Tip: The number on the left is the 'current price'. The one on the right is the 'price change'")
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'company_first_time_tip'))
            ctx.user.new = False
            ctx.session.commit()
        ctx.api.send_chat_message(f"@{ctx.user.name} {', '.join(res)} ")

    @api.command()
    async def stocks(ctx):
        # ctx.api.send_chat_message(f"@{ctx.user.name} Minigame basic commands: !autoinvest, !introduction, !buy, !companies, !all commands, !my stats")
        ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'stocks'))

    @api.command()
    async def introduction(ctx):
        # ctx.api.send_chat_message(f"{ctx.user.name} This is a stock simulation minigame | '!stocks' for basic commands | "
        #                           "Buy stocks for passive income | "
        #                           "Naming Convention: Company[current_price, price_change] ")
        ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'introduction'))

    @my.command()
    async def shares(ctx):
        res = []
        shares = ctx.session.query(db.Shares).filter_by(user_id=ctx.user.id).all()
        if shares:
            for share in shares:
                company = ctx.session.query(Company).get(share.company_id).announcement_description
                res.append(f"{company}: {share.amount}")

            ctx.api.send_chat_message(f'@{ctx.user.name} has {", ".join(res)}')
        else:
            # ctx.api.send_chat_message(f"@{ctx.user.name} doesn't own any shares. Use '!buy' to buy some.")
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'no_shares'))

    @my.command()
    async def points(ctx):
        # ctx.api.send_chat_message(f"@{ctx.user.name} currently has {await ctx.user.points(ctx.api)} {ctx.api.overlord.currency_name}")
        ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'my_points',
                                                         user_points=await ctx.user.points(ctx.api)
                                                         ))

    @my.command()
    async def profit(ctx):
        profit_str = ctx.user.profit_str
        profit = f"@{ctx.user.name} Profit: {profit_str[0]} {ctx.api.overlord.currency_name} | Profit Percentage: {profit_str[1].format(currency_name=ctx.api.overlord.currency_name)}"
        ctx.api.send_chat_message(profit)

    @my.command()
    async def income(ctx):
        res = []
        shares = ctx.session.query(db.Shares).filter_by(user_id=ctx.user.id).all()
        if shares:
            total_income = 0
            for share in shares:
                company = ctx.session.query(Company).get(share.company_id)
                specific_income = ctx.user.passive_income(company, ctx.session)
                total_income += specific_income
                res.append(f"{company.abbv}: {math.ceil(specific_income):,}")

            ctx.api.send_chat_message(f'@{ctx.user.name} {", ".join(res)} | Total: {total_income:,} {ctx.api.overlord.currency_name} per 10 mins.')
        else:
            # ctx.api.send_chat_message(f"@{ctx.user.name} doesn't own any shares. Use '!buy' to buy some.")
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'no_shares'))

    @my.command()
    async def stats(ctx):
        # final_final_res = []
        list_of_income = ''
        total_income = ''

        # !my shares
        res = []
        shares = ctx.session.query(db.Shares).filter_by(user_id=ctx.user.id).all()
        if shares:
            for share in shares:
                company = ctx.session.query(Company).get(share.company_id).announcement_description
                res.append(f"{company}: {share.amount}")

            # final_final_res.append(f'Shares: {", ".join(res)}')
            list_of_shares = f'{", ".join(res)}'
        else:
            # final_final_res.append(f"You don't own any shares. Use '!buy' to buy some.")
            list_of_shares = ctx.api.get_and_format(ctx, 'no_shares')

        # !my income
        res = []
        shares = ctx.session.query(db.Shares).filter_by(user_id=ctx.user.id).all()
        if shares:
            total_income = 0
            for share in shares:
                company = ctx.session.query(Company).get(share.company_id)
                specific_income = ctx.user.passive_income(company, ctx.session)
                total_income += specific_income
                res.append(f"{company.abbv}: {math.ceil(specific_income):,}")

            # final_final_res.append(
            #     f'Income: {", ".join(res)} | Total Income: {total_income} {ctx.api.overlord.currency_name} per 10 mins.')
            list_of_income = f'{", ".join(res)}'
            total_income = f'{total_income}'

        # !my profit
        profit_str = ctx.user.profit_str
        # profit = f"Profit: {profit_str[0]} {ctx.api.overlord.currency_name} | Profit Percentage: {profit_str[1].format(currency_name=ctx.api.overlord.currency_name)}"
        # final_final_res.append(profit)

        # ctx.api.send_chat_message(f'@{ctx.user.name} ' + " ||| ".join(final_final_res))
        ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'my_stats',
                                                         list_of_shares=list_of_shares,
                                                         list_of_income=list_of_income,
                                                         total_income=total_income,
                                                         raw_profit=profit_str[0],
                                                         percentage_profit=profit_str[1].format(currency_name=ctx.api.overlord.currency_name)))

    @next.command()
    async def month(ctx):
        time_since_last_run = time.time() - ctx.api.overlord.last_check
        time_till_next_run = ctx.api.overlord.iterate_cooldown - time_since_last_run
        ctx.api.send_chat_message(f"@{ctx.user.name} The next month starts in {time_till_next_run/60:.0f} minutes")

    @api.command(usage='<budget>')
    async def autoinvest(ctx, budget: IntOrStrAll):
        user_points = await ctx.user.points(ctx.api)
        if budget == 'all':
            budget = user_points
        if budget <= user_points:
            chosen_company = ctx.session.query(db.Company).outerjoin(db.Shares,
                                                                     (db.Shares.user_id == ctx.user.id) & (db.Shares.company_id == Company.id)
                                                                     ).filter(
                db.Company.stock_price.between(3, budget) & (func.coalesce(db.Shares.amount, 0) < ctx.api.overlord.max_stocks_owned)
            ).order_by(func.random()).first()

            if chosen_company:
                stocks_to_buy = math.floor(budget/chosen_company.stock_price)
                if stocks_to_buy <= 0:
                    # ctx.api.send_chat_message(f"@{ctx.user.name} too small budget. No stocks bought.")
                    ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'autoinvest_budget_too_small_for_companies'))
                    return
                await buy.run(ctx, stocks_to_buy, chosen_company)
            else:
                # ctx.api.send_chat_message(f"@{ctx.user.name} too small budget. No stocks bought.")
                total_shares = 0
                for share in ctx.user.shares:
                    total_shares += share.amount
                if total_shares >= ctx.api.overlord.max_stocks_owned * ctx.session.query(Company).count():
                    ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'reached_stocks_limit_on_everything'))
                else:
                    ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'autoinvest_budget_too_small_for_companies'))
        else:
            # ctx.api.send_chat_message(f"@{ctx.user.name} you need {budget} {ctx.api.overlord.currency_name}, aka you need {budget-user_points} more.")
            ctx.api.send_chat_message(ctx.api.get_and_format(ctx, 'autoinvest_budget_too_small_for_available_points',
                                                             budget=f'{budget:,}',
                                                             budget_points_difference=f'{budget-user_points:,}'))

    @api.command()
    async def about(ctx):
        # ctx.api.send_chat_message(f"@{ctx.user.name} This minigame is open-source and it was made by Razbi and Nesami. Github link: https://github.com/TheRealRazbi/Stocks-of-Razbia")
        ctx.api.send_chat_message(f'@{ctx.user.name} This minigame is open-source and it was made by Razbi and Nesami. '
                                  'Github link: https://github.com/TheRealRazbi/Stocks-of-Razbia')


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
