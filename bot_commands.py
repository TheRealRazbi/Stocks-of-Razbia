import math

from sqlalchemy import func

from API import API

from database import Company
import database as db
from utils import create_embed
from multi_arg import IntOrStrAll, CompanyOrIntOrAll
import commands as commands_
import time
from typing import Union
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle

from utils import EmbedColor


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

        await ctx.send_message(f"All minigame-related chat commands: {', '.join(thing_to_display)}")

    @api.command(usage="<company> <budget>")
    async def buy(ctx, company: CompanyOrIntOrAll, amount: CompanyOrIntOrAll):
        amount: Union[Company, int, 'all']
        company: Union[Company, int, 'all']
        if isinstance(company, Company) and not isinstance(amount, Company):
            pass
        elif not isinstance(company, Company) and isinstance(amount, Company):
            company, amount = amount, company
        elif isinstance(company, Company) and isinstance(amount, Company):
            # await ctx.send_message(f"@{ctx.user.name} inputted 2 companies. You need to input a number and a company.")
            await ctx.send_message(ctx.api.get_and_format(ctx, 'buy_or_sell_2_companies'))
            return
        elif not isinstance(company, Company) and not isinstance(amount, Company):
            # await ctx.send_message(f"@{ctx.user.name} didn't input any company. You need to input a number and a company.")
            await ctx.send_message(ctx.api.get_and_format(ctx, 'buy_or_sell_0_companies'))
            return

        points = await ctx.user.points(ctx.api, ctx.session)
        if amount == 'all':
            amount = math.floor(points / company.stock_price)
            if amount == 0:
                await ctx.send_message(f"{ctx.user.name} doesn't have enough points to buy even 1 stock.")
        else:
            amount = math.floor(amount / company.stock_price)

        if share := ctx.session.query(db.Shares).get((ctx.user.id, company.id)):
            stocks_till_100k = 100_000 - share.amount
            if stocks_till_100k == 0:
                await ctx.send_message(ctx.api.get_and_format(ctx, 'reached_stocks_limit', company_abbv=company.abbv))
                return
            amount = min(amount, stocks_till_100k)
        else:
            amount = min(amount, 100_000)

        if amount <= 0:
            await ctx.send_message(ctx.api.get_and_format(ctx, 'budget_too_small', points=f'{points}',
                                                          company_price=f'{company.stock_price:.1f}'))
            return

        cost = math.ceil(amount * company.stock_price)
        if points >= cost:
            if share:
                share.amount += amount
            else:
                share = db.Shares(user_id=ctx.user.id, company_id=company.id, amount=amount)
                ctx.session.add(share)
            company.increase_chance = max(50 - .001 * company.stocks_bought, 45)
            ctx.session.commit()
            await ctx.api.upgraded_add_points(ctx.user, -cost, ctx.session)
            # await ctx.send_message(f"@{ctx.user.name} just bought {amount} stocks from [{company.abbv}] '{company.full_name}' for {cost} {ctx.api.overlord.currency_name}. "
            #                           f"Now they gain {math.ceil(share.amount*company.stock_price*.1)} {ctx.api.overlord.currency_name} from {company.abbv} each 10 mins. ")
            await ctx.send_message(ctx.api.get_and_format(ctx, 'buy_successful',
                                                          amount=f'{amount:,}',
                                                          company_abbv=company.abbv,
                                                          company_full_name=company.full_name,
                                                          cost=f'{cost:,}',
                                                          passive_income=f'{ctx.user.passive_income(company, ctx.session):,}'))

        else:
            # await ctx.send_message(f"@{ctx.user.name} has {points:,} {ctx.api.overlord.currency_name} and requires {cost} aka {cost-points} more.")
            await ctx.send_message(ctx.api.get_and_format(ctx, 'buy_not_enough_points',
                                                          points=f'{points:,}',
                                                          cost=f'{cost:,}',
                                                          cost_minus_points=f'{cost - points:,}'))

    @api.command(usage="<company> <amount>")
    async def sell(ctx, company: CompanyOrIntOrAll, amount: CompanyOrIntOrAll):
        if isinstance(company, Company) and not isinstance(amount, Company):
            pass
        elif not isinstance(company, Company) and isinstance(amount, Company):
            company, amount = amount, company
        elif isinstance(company, Company) and isinstance(amount, Company):
            await ctx.send_message(f"@{ctx.user.name} You input 2 companies. you need to input a value and a company")
            return
        elif not isinstance(company, Company) and not isinstance(amount, Company):
            await ctx.send_message(
                f"@{ctx.user.name} You didn't input any company. you need to input a value and a company")
            return

        if amount != 'all':
            amount = math.ceil(amount / company.stock_price)

        share = ctx.session.query(db.Shares).get((ctx.user.id, company.id))
        if amount == 'all' and share or share and share.amount >= amount:
            if amount == 'all':
                amount = share.amount
            if amount <= 0:
                await ctx.send_message(ctx.api.get_and_format(ctx, 'number_too_small'))
                return
            cost = math.ceil(amount * company.stock_price)

            await ctx.api.upgraded_add_points(ctx.user, cost, ctx.session)
            share.amount -= amount
            if share.amount == 0:
                ctx.session.delete(share)
            company.increase_chance = max(50 - .01 * company.stocks_bought, 45)
            ctx.session.commit()
            # await ctx.send_message(f"@{ctx.user.name} has sold {amount} stocks from [{company.abbv}] '{company.full_name}' for {cost} {ctx.api.overlord.currency_name}.")
            await ctx.send_message(ctx.api.get_and_format(ctx, 'sell_successful',
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
                                                 needed_amount=f'{math.floor(share.amount * company.stock_price):,}',
                                                 amount=f'{amount:,}')
            await ctx.send_message(message)

    @api.command()
    async def sellall(ctx):
        total_outcome = 0
        list_of_all_sells = []
        shares_ = ctx.user.get_all_owned_stocks(ctx.session)
        if not len(shares_):
            await ctx.send_message(ctx.api.get_and_format(ctx, 'no_shares'))
            return
        for share in shares_:
            company_ = share.company
            total_outcome += math.ceil(share.amount * company_.stock_price)
            list_of_all_sells.append(f'{company_.abbv}: {share.amount:,}')
            ctx.session.delete(share)
        await ctx.api.upgraded_add_points(ctx.user, total_outcome, ctx.session)
        ctx.session.commit()
        list_of_all_sells = ", ".join(list_of_all_sells)
        await ctx.send_message(ctx.api.get_and_format(ctx, 'sell_everything_successful',
                                                      list_of_all_sells=list_of_all_sells,
                                                      total_outcome=f'{total_outcome:,}'))

    @api.command(usage="<company>")
    async def company(ctx, company: Company):
        if ctx.discord_message:
            embed = company.embed
            await ctx.send_message(embed=embed)
        else:
            await ctx.send_message(company)

    @api.command()
    async def companies(ctx):
        if ctx.discord_message:
            companies_ = ctx.session.query(db.Company).order_by(Company.stock_price.desc()).all()
            embed_content = {company_.abbv: company_.price_and_price_diff for company_ in companies_}
            footer = "Tip: The number on the left is the 'current price'. The one on the right is the 'price change'."
            embed = create_embed(title='!companies', content=embed_content, footer=footer)

            await ctx.send_message(embed=embed, no_reply=True)

        else:
            res = []
            companies = ctx.session.query(db.Company).order_by(Company.stock_price.desc()).all()
            for company in companies:
                # message = f"{company.abbv.upper()}[{company.stock_price-company.price_diff:.1f}{company.price_diff:+}]"
                # message = f"{company.abbv.upper()}[{company.stock_price:.1f}{company.price_diff/company.stock_price*100:+.1f}%]"
                message = company.announcement_description
                res.append(message)
            if ctx.user.new:
                # await ctx.send_message(f"@{ctx.user.name} Tip: The number on the left is the 'current price'. The one on the right is the 'price change'")
                await ctx.send_message(ctx.api.get_and_format(ctx, 'company_first_time_tip'))
                ctx.user = ctx.user.refresh(session=ctx.session)
                ctx.user.new = False
                ctx.session.commit()

                await ctx.send_message(f"@{ctx.user.name} {', '.join(res)} ")

    @api.command()
    async def stocks(ctx):
        # await ctx.send_message(f"@{ctx.user.name} Minigame basic commands: !autoinvest, !introduction, !buy, !companies, !all commands, !my stats")
        await ctx.send_message(ctx.api.get_and_format(ctx, 'stocks'))

    @api.command()
    async def introduction(ctx):
        # await ctx.send_message(f"{ctx.user.name} This is a stock simulation minigame | '!stocks' for basic commands | "
        #                           "Buy stocks for passive income | "
        #                           "Naming Convention: Company[current_price, price_change] ")
        await ctx.send_message(ctx.api.get_and_format(ctx, 'introduction'))

    @api.command()
    async def leaderboard(ctx):  # TODO make it appear discord name instead of twitch name
        await show_top(ctx, amount=5)

    @api.command()
    async def top(ctx, amount):
        await show_top(ctx, amount)

    async def show_top(ctx, amount):
        amount = min(abs(amount), 20)
        if amount == 0:
            # await ctx.send_message("")
            return
        users = ctx.session.query(db.User).order_by(db.User.last_worth_checked.desc()).limit(amount).all()
        embed = create_embed(title="Leaderboard Net Worth", color=EmbedColor.BLUE)
        for user in users:
            # embed.add_field(name=user.name, value=await user.total_worth(ctx.api, ctx.session), inline=False)
            embed.add_field(name=user.name, value=user.last_worth_checked, inline=False)

        # content = {user.name: await user.total_worth(ctx.api, ctx.session) for user in users}
        msg = await ctx.send_message(embed=embed)
        buttons = [
            create_button(style=ButtonStyle.green, label="Net Worth"),

        ]

    @my.command()
    async def points(ctx):
        stocks_worth = ctx.user.stocks_worth(session=ctx.session)
        points_ = await ctx.user.points(api=ctx.api, session=ctx.session)
        message = f"@{ctx.user.name} currently has {points_} ""{currency_name} and owns "f"stocks worth {stocks_worth} ""{currency_name}. " \
                  f"Total: {points_ + stocks_worth}"
        await ctx.send_message(message.format(currency_name=ctx.api.overlord.currency_name))

    @my.command()
    async def shares(ctx):
        res = []
        shares = ctx.session.query(db.Shares).filter_by(user_id=ctx.user.id).all()
        if shares:
            for share in shares:
                company = ctx.session.query(Company).get(share.company_id).announcement_description
                res.append(f"{company}: {share.amount}")

            await ctx.send_message(f'@{ctx.user.name} has {", ".join(res)}')
        else:
            # await ctx.send_message(f"@{ctx.user.name} doesn't own any shares. Use '!buy' to buy some.")
            await ctx.send_message(ctx.api.get_and_format(ctx, 'no_shares'))

    # @my.command()
    # async def old_points(ctx):
    #     # await ctx.send_message(f"@{ctx.user.name} currently has {await ctx.user.points(ctx.api)} {ctx.api.overlord.currency_name}")
    #     await ctx.send_message(ctx.api.get_and_format(ctx, 'my_points',
    #                                                   user_points=f'{await ctx.user.points(ctx.api, ctx.session):,}'
    #                                                   ))

    @api.command()
    async def fastforward(ctx, minutes: int):
        if ctx.discord_message:
            if ctx.user.discord_id == '241244277382971399':
                ctx.api.overlord.last_check -= 60 * minutes
                await ctx.send_message(f"Travelled through time by {minutes} minutes")
            else:
                await ctx.send_message(f"Only Razbi can use it")

    @my.command()
    async def profit(ctx):
        profit_str = await ctx.user.profit_str(ctx.api, ctx.session)
        profit_ = f"@{ctx.user.name} Profit: {profit_str[0]} {ctx.api.overlord.currency_name} | Profit Percentage: {profit_str[1].format(currency_name=ctx.api.overlord.currency_name)}"
        await ctx.send_message(profit_)

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

            await ctx.send_message(
                f'@{ctx.user.name} {", ".join(res)} | Total: {total_income:,} {ctx.api.overlord.currency_name} per 10 mins.')
        else:
            # await ctx.send_message(f"@{ctx.user.name} doesn't own any shares. Use '!buy' to buy some.")
            await ctx.send_message(ctx.api.get_and_format(ctx, 'no_shares'))

    @my.command()
    async def stats(ctx):
        if ctx.discord_message:
            footer = None
            if ctx.user.discord_id == '299225310556061696':
                footer = 'No refunding kidneys'
            embed = create_embed(f"{ctx.discord_message.author.name}'s Stats", footer=footer)
            embed.add_field(name=f'{"Shares":=^30}', value='⠀', inline=False)
            shares = ctx.session.query(db.Shares).filter_by(user_id=ctx.user.id).all()
            total_income = 0
            if shares:
                for share in shares:
                    company = ctx.session.query(Company).get(share.company_id)
                    embed.add_field(name=f'{company.announcement_description}',
                                    value=f'{share.amount} shares │ {company.stock_price:.0f} points per share',
                                    inline=True)

                embed.add_field(name=f"{'Income':=^30}", value='⠀', inline=False)
                for share in shares:
                    company = ctx.session.query(Company).get(share.company_id)
                    specific_income = ctx.user.passive_income(company, ctx.session)
                    total_income += specific_income
                    embed.add_field(name=f"{company.abbv}", value=f"{math.ceil(specific_income):,}")

            else:
                embed.add_field(name='⠀', value="Doesn't have any shares", inline=True)

            raw_profit, percentage_profit = await ctx.user.profit_str(ctx.api, session=ctx.session)
            embed.add_field(name=f"{'Profit':=^30}", value=f'{raw_profit} points', inline=False)
            embed.add_field(name='Profit Percentage',
                            value=f'{percentage_profit.format(currency_name=ctx.api.overlord.currency_name)}')
            # 'Profit: {raw_profit} {currency_name} | Profit Percentage: {percentage_profit}'
            await ctx.send_message(embed=embed)

        else:
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
            profit_str = await ctx.user.profit_str(ctx.api, ctx.session)
            # profit = f"Profit: {profit_str[0]} {ctx.api.overlord.currency_name} | Profit Percentage: {profit_str[1].format(currency_name=ctx.api.overlord.currency_name)}"
            # final_final_res.append(profit)

            # await ctx.send_message(f'@{ctx.user.name} ' + " ||| ".join(final_final_res))
            await ctx.send_message(ctx.api.get_and_format(ctx, 'my_stats',
                                                          list_of_shares=list_of_shares,
                                                          list_of_income=list_of_income,
                                                          total_income=total_income,
                                                          raw_profit=profit_str[0],
                                                          percentage_profit=profit_str[1].format(
                                                              currency_name=ctx.api.overlord.currency_name)))

    @next.command()
    async def month(ctx):
        time_since_last_run = time.time() - ctx.api.overlord.last_check
        time_till_next_run = ctx.api.overlord.iterate_cooldown - time_since_last_run
        await ctx.send_message(f"@{ctx.user.name} The next month starts in {time_till_next_run / 60:.0f} minutes")

    @next.command()
    async def event(ctx):
        time_since_last_run = time.time() - ctx.api.overlord.last_check
        time_till_next_run = ctx.api.overlord.iterate_cooldown - time_since_last_run
        time_till_next_event = time_till_next_run + \
                               (4 - ctx.api.overlord.months % 4) * ctx.api.overlord.iterate_cooldown
        await ctx.send_message(f'The next event starts in {time_till_next_event // 60:.0f} minutes')

    @api.command(usage='<budget>')
    async def autoinvest(ctx, budget: IntOrStrAll):
        user_points = await ctx.user.points(ctx.api, ctx.session)
        if budget == 'all':
            budget = user_points
        if budget <= user_points:
            chosen_company = ctx.session.query(db.Company).outerjoin(db.Shares,
                                                                     (db.Shares.user_id == ctx.user.id) & (
                                                                             db.Shares.company_id == Company.id)
                                                                     ).filter(
                db.Company.stock_price.between(3, budget) & (
                        func.coalesce(db.Shares.amount, 0) < ctx.api.overlord.max_stocks_owned)
            ).order_by(func.random()).first()

            if chosen_company:
                # stocks_to_buy = math.floor(budget / chosen_company.stock_price)
                # if stocks_to_buy <= 0:
                #     # await ctx.send_message(f"@{ctx.user.name} too small budget. No stocks bought.")
                #     await ctx.send_message(ctx.api.get_and_format(ctx, 'autoinvest_budget_too_small_for_companies'))
                #     return
                await buy.run(ctx, budget, chosen_company)
            else:
                # await ctx.send_message(f"@{ctx.user.name} too small budget. No stocks bought.")
                total_shares = 0
                for share in ctx.user.shares:
                    total_shares += share.amount
                if total_shares >= ctx.api.overlord.max_stocks_owned * ctx.session.query(Company).count():
                    await ctx.send_message(ctx.api.get_and_format(ctx, 'reached_stocks_limit_on_everything'))
                else:
                    await ctx.send_message(ctx.api.get_and_format(ctx, 'autoinvest_budget_too_small_for_companies'))
        else:
            # await ctx.send_message(f"@{ctx.user.name} you need {budget} {ctx.api.overlord.currency_name}, aka you need {budget-user_points} more.")
            await ctx.send_message(ctx.api.get_and_format(ctx, 'autoinvest_budget_too_small_for_available_points',
                                                          budget=f'{budget:,}',
                                                          budget_points_difference=f'{budget - user_points:,}'))

    @api.command()
    async def about(ctx):
        # await ctx.send_message(f"@{ctx.user.name} This minigame is open-source and it was made by Razbi and Nesami. Github link: https://github.com/TheRealRazbi/Stocks-of-Razbia")
        await ctx.send_message(f'@{ctx.user.name} This minigame is open-source and it was made by Razbi and Nesami. '
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
    # ctx = Context(api, user)
    # prepared_args = prepare_args(ctx, command, args)
    # command(ctx, *args)
