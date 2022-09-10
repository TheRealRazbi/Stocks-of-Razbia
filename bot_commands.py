import math
from enum import Enum
import random

import discord
from discord import ui
from sqlalchemy import func
from sqlalchemy.future import select

import database
from API import API

from database import Company, User
import database as db
from utils import create_embed
from multi_arg import AllStr, Percent, StocksStr
import commands as commands_
import time
from typing import Optional
from utils import EmbedColor


def register_commands(api: API):
    my = api.group(name="my", available_on_twitch=True)
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

    @api.command(usage="<company> <budget>", unordered_args=True, sequence_arg='companies', available_on_twitch=True,
                 specific_arg_usage={'amount': "Budget has to be either an integer, 'all' or a percentage like '50%'",
                                     'companies': "Company has to exist and has to be a valid abbreviation like 'rzbi'"})
    async def buy(ctx, companies: [Company], amount: [AllStr, int, Percent], shares: Optional[StocksStr] = None):
        unsent_messages = []
        old_send_message = ctx.send_message

        async def buy_send_message(message):
            unsent_messages.append(message)

        async def send_everything():
            if ctx.discord_message:
                await old_send_message('\n'.join(unsent_messages))
            else:
                await old_send_message(' | '.join(unsent_messages))

        ctx.send_message = buy_send_message

        points = await ctx.user.points(ctx.api, ctx.session)

        if amount == 'all':
            amount = math.floor(points)
            if amount == 0:
                message = f"@{ctx.user.name} doesn't have enough points to buy even 1 share. They have {points} points. "
                one_share_is = f"1 share is {companies[0].stock_price:.0f} points" if len(companies) == 1 else ''
                await ctx.send_message(message + one_share_is)
                await send_everything()
                return
        elif isinstance(amount, float) and 1 >= amount > 0:
            amount = math.floor(points * amount)

        amount_before_iteration = amount
        for company in companies:
            points = await ctx.user.points(ctx.api, ctx.session)
            amount = amount_before_iteration / len(companies)
            if not shares:
                amount = math.floor(amount / company.stock_price)

            # if share := ctx.session.query(db.Shares).get((ctx.user.id, company.id)):
            if share := await ctx.session.get(db.Shares, (ctx.user.id, company.id)):
                stocks_till_100k = 100_000 - share.amount
                if stocks_till_100k == 0:
                    await ctx.send_message(
                        ctx.api.get_and_format(ctx, 'reached_stocks_limit', company_abbv=company.abbv))
                    continue
                amount = min(amount, stocks_till_100k)
            else:
                amount = min(amount, 100_000)

            if amount <= 0:
                if shares:
                    await ctx.send_message(ctx.api.get_and_format(ctx, 'number_too_small', points=f'{points}',
                                                                  company_price=f'{company.stock_price:.1f}'))
                else:
                    await ctx.send_message(ctx.api.get_and_format(ctx, 'budget_too_small', points=f'{points}',
                                                                  company_price=f'{company.stock_price:.1f}'))
                await send_everything()
                return

            cost = math.ceil(amount * company.stock_price)
            if points < cost:
                amount = math.floor(points / company.stock_price)
                if amount > 0:
                    cost = math.ceil(amount * company.stock_price)

            if points >= cost:
                if share:
                    share.amount += amount
                else:
                    share = db.Shares(user_id=ctx.user.id, company_id=company.id, amount=amount)
                    ctx.session.add(share)
                company.increase_chance = max(50 - .0001 * await company.stocks_bought(session=ctx.session), 45)
                await ctx.session.commit()
                await ctx.api.upgraded_add_points(ctx.user, -cost, ctx.session)
                await ctx.send_message(ctx.api.get_and_format(ctx, 'buy_successful',
                                                              amount=f'{amount:,}',
                                                              company_abbv=company.abbv,
                                                              company_full_name=company.full_name,
                                                              cost=f'{cost:,}',
                                                              passive_income=f'{await ctx.user.passive_income(company, ctx.session):,}'))

            else:
                await ctx.send_message(ctx.api.get_and_format(ctx, 'buy_not_enough_points',
                                                              points=f'{points:,}',
                                                              cost=f'{cost:,}',
                                                              cost_minus_points=f'{cost - points:,}'))
        await send_everything()

    @api.command(usage="<company> <budget>", unordered_args=True, sequence_arg='companies', available_on_twitch=True,
                 specific_arg_usage={'amount': "Budget has to be either an integer, 'all' or a percentage like '50%'",
                                     'companies': "Company has to exist and has to be a valid abbreviation like 'rzbi'"})
    async def sell(ctx, companies: [Company], amount: [int, AllStr, Percent], use_shares: Optional[StocksStr] = None):
        amount_before_iteration = amount
        unsent_messages = []
        old_send_message = ctx.send_message

        async def buy_send_message(message):
            unsent_messages.append(message)

        async def send_everything():
            await old_send_message('\n'.join(unsent_messages))

        ctx.send_message = buy_send_message
        for company in companies:
            amount = amount_before_iteration

            if isinstance(amount, int) and not use_shares:
                amount = math.ceil(amount / company.stock_price)

            share = ctx.session.query(db.Shares).get((ctx.user.id, company.id))
            if isinstance(amount, float):
                amount = math.floor(share.amount * amount)
            if amount == 'all' and share or share:
                if amount == 'all' or amount >= share.amount:
                    amount = share.amount
                if amount <= 0:
                    await ctx.send_message(ctx.api.get_and_format(ctx, 'number_too_small'))
                    await send_everything()
                    return
                cost = math.ceil(amount * company.stock_price)

                await ctx.api.upgraded_add_points(ctx.user, cost, ctx.session)
                share.amount -= amount
                if share.amount == 0:
                    ctx.session.delete(share)
                company.increase_chance = max(50 - .0001 * company.stocks_bought, 45)
                ctx.session.commit()
                await ctx.send_message(ctx.api.get_and_format(ctx, 'sell_successful',
                                                              amount=f'{amount:,.0f}',
                                                              company_abbv=company.abbv,
                                                              company_full_name=company.full_name,
                                                              cost=f'{cost:,}'))
            else:
                if not share:
                    message = ctx.api.get_and_format(ctx, 'sell_no_shares',
                                                     company_abbv=company.abbv)
                else:
                    message = ctx.api.get_and_format(ctx, 'sell_not_enough_shares',
                                                     company_abbv=company.abbv,
                                                     needed_amount=f'{math.floor(share.amount * company.stock_price):,}',
                                                     amount=f'{amount:,}')
                await ctx.send_message(message)
        await send_everything()

    @api.command(available_on_twitch=True)
    async def sellall(ctx):
        total_outcome = 0
        list_of_all_sells = []
        shares_ = await ctx.user.get_all_owned_stocks(ctx.session)
        if not len(shares_):
            await ctx.send_message(ctx.api.get_and_format(ctx, 'no_shares'))
            return
        for share in shares_:
            if company_ := await ctx.session.get(Company, share.company_id):
                total_outcome += math.ceil(share.amount * company_.stock_price)
                list_of_all_sells.append(f'{company_.abbv}: {share.amount:,}')
                await ctx.session.delete(share)
                company_.increase_chance = max(50 - .001 * await company_.stocks_bought(session=ctx.session), 45)
        await ctx.api.upgraded_add_points(ctx.user, total_outcome, ctx.session)
        await ctx.session.commit()
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

    @api.command(available_on_twitch=True)
    async def companies(ctx):
        if ctx.discord_message:
            companies_ = ctx.session.query(db.Company).order_by(Company.stock_price.desc()).all()
            embed_content = {f'[{company_.abbv}]': company_.price_and_price_diff for company_ in companies_}
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
            # if ctx.user.new:
            #     # await ctx.send_message(f"@{ctx.user.name} Tip: The number on the left is the 'current price'. The one on the right is the 'price change'")
            #     await ctx.send_message(ctx.api.get_and_format(ctx, 'company_first_time_tip'))
            #     ctx.user = ctx.user.refresh(session=ctx.session)
            #     ctx.user.new = False
            #     ctx.session.commit()

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
    async def leaderboard(ctx):
        if ctx.discord_message:
            await show_top(ctx, amount=5)
        else:
            pass  # TODO: add a top for twitch as well

    @api.command()
    async def refresh_leaderboard(ctx):
        if ctx.user.discord_id == '241244277382971399':
            ctx.api.discord_manager.cached_usernames.clear()
            users = ctx.session.query(database.User).all()
            for user in users:
                await user.points(ctx.api, ctx.session)
                user.update_last_checked_income(ctx.session)
            await ctx.send_message("Refreshed leaderboard")
        else:
            await ctx.send_message("Only Razbi can use this command")

    @api.command()
    async def top(ctx, amount: int):
        if ctx.discord_message:
            await show_top(ctx, amount=amount)

    class PossibleLeaderboards(Enum):
        NET_WORTH = {"order_by": 'last_worth_checked', "color": EmbedColor.GREEN, 'title': "Leaderboard Net Worth",
                     "message_after_value": 'net worth'}
        BALANCE = {"order_by": 'last_balance_checked', "color": EmbedColor.GREEN, 'title': "Leaderboard Balance",
                   "message_after_value": 'points'}
        MOST_STOCKS_OWNED = {"order_by": 'last_most_stocks_owned_checked', "color": EmbedColor.GREEN,
                             'title': "Leaderboard Most Stocks Owned", "message_after_value": 'stocks owned'}
        MOST_STOCKS_WORTH = {"order_by": 'last_most_stocks_worth_checked', "color": EmbedColor.GREEN,
                             'title': "Leaderboard Most Stocks Worth", "message_after_value": 'stocks worth'}
        INCOME = {"order_by": "last_income_checked", "color": EmbedColor.GREEN, "title": "Leaderboard Income",
                  "message_after_value": "income"}

    async def get_leaderboard_embed(ctx, amount,
                                    leaderboard_type: PossibleLeaderboards = PossibleLeaderboards.NET_WORTH):
        amount = min(abs(amount), 20)
        if amount == 0:
            # await ctx.send_message("")
            return
        users = ctx.session.query(db.User).order_by(getattr(db.User, leaderboard_type.value['order_by']).desc()).limit(
            amount).all()
        usernames = {}
        for user in users:
            usernames[user.name] = ctx.api.discord_manager.get_user(int(user.discord_id))

        embed = create_embed(title=leaderboard_type.value['title'], color=leaderboard_type.value['color'])
        # print("Embed before adding fields")
        for index, user in enumerate(users):
            # embed.add_field(name=user.name, value=await user.total_worth(ctx.api, ctx.session), inline=False)
            value = getattr(user, leaderboard_type.value['order_by'])
            if isinstance(value, int):
                value = f'{value:,} {leaderboard_type.value["message_after_value"]}'
                name = f'{usernames[user.name]} {"🥇" if index == 0 else ""}'

                embed.add_field(name=name, value=value, inline=False)

        # print("Embed for leaderboard ready")
        # content = {user.name: await user.total_worth(ctx.api, ctx.session) for user in users}
        return embed

    class LeaderboardView(ui.View):
        def __init__(self, ctx, amount):
            super(LeaderboardView, self).__init__()
            self.last_button_pressed = None
            self.amount = amount
            self.ctx = ctx

        async def update_embed(self, button_instance, interaction, leaderboard_type: PossibleLeaderboards):
            for button in self.children:
                if button.disabled:
                    button.disabled = False
            button_instance.disabled = True
            self.last_button_pressed = button_instance
            embed_ = await get_leaderboard_embed(self.ctx, self.amount, leaderboard_type=leaderboard_type)
            await interaction.response.edit_message(embed=embed_, view=self)

        @ui.button(label="Net Worth", style=discord.ButtonStyle.gray, disabled=True)
        async def net_worth(self, interaction, button):
            await self.update_embed(button_instance=button, interaction=interaction,
                                    leaderboard_type=PossibleLeaderboards.NET_WORTH)

        @ui.button(label='Balance', style=discord.ButtonStyle.gray)
        async def balance(self, interaction, button):
            await self.update_embed(button_instance=button, interaction=interaction,
                                    leaderboard_type=PossibleLeaderboards.BALANCE)

        @ui.button(label="Most Stocks Owned", style=discord.ButtonStyle.gray)
        async def most_stocks_owned(self, interaction, button):
            await self.update_embed(button_instance=button, interaction=interaction,
                                    leaderboard_type=PossibleLeaderboards.MOST_STOCKS_OWNED)

        @ui.button(label="Most Stocks Worth", style=discord.ButtonStyle.gray)
        async def most_stocks_worth(self, interaction, button):
            await self.update_embed(button_instance=button, interaction=interaction,
                                    leaderboard_type=PossibleLeaderboards.MOST_STOCKS_WORTH)

        @ui.button(label="Income", style=discord.ButtonStyle.gray)
        async def income(self, interaction, button):
            await self.update_embed(button_instance=button, interaction=interaction,
                                    leaderboard_type=PossibleLeaderboards.INCOME)

        # @ui.button(label=' ', disabled=True)
        # async def anti_ocd_button(self, interaction, button):
        #     pass

        @ui.button(label='', style=discord.ButtonStyle.green, emoji='➕')
        async def plus_one(self, interaction, button):
            if self.amount < 10:
                self.amount += 1
                if self.last_button_pressed is None:
                    await self.net_worth.callback(interaction)
                else:
                    await self.last_button_pressed.callback(interaction)
            else:
                await interaction.response.edit_message()

        @ui.button(label='', style=discord.ButtonStyle.red, emoji='➖')
        async def minus_one(self, interaction, button):
            if self.amount > 1:
                self.amount -= 1
                if self.last_button_pressed is None:
                    await self.net_worth.callback(interaction)
                else:
                    await self.last_button_pressed.callback(interaction)
            else:
                await interaction.response.edit_message()

    async def show_top(ctx, amount: int):
        embed = await get_leaderboard_embed(ctx, amount=amount)
        view = LeaderboardView(ctx=ctx, amount=amount)
        await ctx.send_message(embed=embed, view=view)

    @my.command()
    async def points(ctx):
        stocks_worth = ctx.user.stocks_worth(session=ctx.session)
        points_ = await ctx.user.points(api=ctx.api, session=ctx.session)
        message = f"@{ctx.user.name} currently has {points_:,} ""{currency_name} and owns "f"stocks worth {stocks_worth:,} ""{currency_name}. " \
                  f"Total: {points_ + stocks_worth:,}"" {currency_name}"
        await ctx.send_message(message.format(currency_name=ctx.api.overlord.currency_name))

    @my.command()
    async def shares(ctx):
        if not ctx.discord_message:  # TODO: add an embed here
            pass
        else:
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
        # profit_ = f"@{ctx.user.name} Profit: {profit_str[0]} {ctx.api.overlord.currency_name} | Profit Percentage: {profit_str[1].format(currency_name=ctx.api.overlord.currency_name)}"
        profit_ = f"@{ctx.user.name} Profit: {profit_str} {ctx.api.overlord.currency_name}"
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

            ctx.user.last_income_checked = total_income
            ctx.session.commit()
            await ctx.send_message(
                f'@{ctx.user.name} {", ".join(res)} | Total: {total_income:,} {ctx.api.overlord.currency_name} per 10 mins.')
        else:
            ctx.user.last_income_checked = 0
            ctx.session.commit()
            # await ctx.send_message(f"@{ctx.user.name} doesn't own any shares. Use '!buy' to buy some.")
            await ctx.send_message(ctx.api.get_and_format(ctx, 'no_shares'))

    @api.command()
    async def states(ctx):
        await ctx.send_message(
            "Alabama, Alaska, Arizona, Arkansas, California, Colorado, Connecticut, Delaware, Florida "
            "Georgia, Hawaii, Idaho, Illinois, Indiana, Iowa, Kansas, Kentucky, Louisiana, Maine, Maryland, "
            "Massachusetts, Michigan, Minnesota, Mississippi, Missouri, Montana, Nebraska, Nevada, New Hampshire, "
            "New Jersey, New Mexico, New York, North Carolina, North Dakota, Ohio, Oklahoma, Oregon, Pennsylvania, "
            "Rhode Island, South Carolina, South Dakota, Tennessee, Texas, Utah, Vermont, Virginia, Washington, "
            "West Virginia, Wisconsin, Wyoming")

    @my.command(available_on_twitch=True)
    async def stats(ctx, user: Optional[User] = None):
        if ctx.discord_message:

            if user is None:
                user = ctx.user
                author_name = ctx.discord_message.author.name
            else:
                user = user.refresh(session=ctx.session)
                author_name = ctx.api.discord_manager.get_user(int(user.discord_id)).name

            footer = None
            if user.discord_id == '299225310556061696':
                footer = 'No refunding kidneys'
            embed = create_embed(f"{author_name}'s Stats", footer=footer)
            embed.add_field(name=f'{" Shares ":=^30}', value='⠀', inline=False)
            shares = ctx.session.query(db.Shares).filter_by(user_id=user.id).all()
            total_income = 0
            total_shares = 0
            stocks_worth = 0
            if shares:
                for share in shares:
                    company = ctx.session.query(Company).get(share.company_id)
                    embed.add_field(name=f'[{company.abbv.upper()}]',
                                    value=f'Total: {share.amount:,} shares\n'
                                          f'Value: {company.stock_price:.0f} points\n'
                                          f'Change: {-company.price_diff:+.1f} points ({company.price_diff_percent:.1f}%)',
                                    inline=True)
                    total_shares += share.amount
                stocks_worth = user.stocks_worth(session=ctx.session)
                embed.add_field(name="Shares",
                                value=f'{total_shares:,} shares worth {stocks_worth:,} points')

                embed.add_field(name=f"{' Income ':=^30}", value='⠀', inline=False)
                for share in shares:
                    company = ctx.session.query(Company).get(share.company_id)
                    specific_income = user.passive_income(company, ctx.session)
                    total_income += specific_income
                    embed.add_field(name=f"[{company.abbv}]", value=f"{math.ceil(specific_income):,} points (10min)")
                embed.add_field(name="Total Income", value=f'{total_income:,} points (10min)', inline=False)
                user.last_income_checked = total_income
                ctx.session.commit()
            else:
                ctx.user.last_income_checked = 0
                ctx.session.commit()
                embed.add_field(name='⠀', value="Doesn't have any shares", inline=True)

            points = await user.points(api=ctx.api, session=ctx.session)
            embed.add_field(name="Balance", value=f'{points:,} points')
            embed.add_field(name="Net Worth", value=f'{points + stocks_worth:,} points')
            raw_profit = await user.profit_str(ctx.api, session=ctx.session)
            embed.add_field(name=f"Profit", value=f'{raw_profit} points')
            # embed.add_field(name='Profit Percentage',
            #                 value=f'{percentage_profit.format(currency_name=ctx.api.overlord.currency_name)}')
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
                                                          raw_profit=profit_str,
                                                          points=await ctx.user.points(api=ctx.api, session=ctx.session)
                                                          # percentage_profit=profit_str[1].format(
                                                          #     currency_name=ctx.api.overlord.currency_name))
                                                          ))

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
                               ((4 - ctx.api.overlord.months % 4) - 1) * ctx.api.overlord.iterate_cooldown
        await ctx.send_message(f'The next event starts in {time_till_next_event // 60:.0f} minutes')

    @api.command(usage='<budget>', available_on_twitch=True)
    async def autoinvest(ctx, budget: [int, AllStr]):
        user_points = await ctx.user.points(ctx.api, ctx.session)
        if budget == 'all':
            budget = user_points
        if budget <= user_points:
            # chosen_company = ctx.session.query(db.Company).outerjoin(db.Shares,
            #                                                          (db.Shares.user_id == ctx.user.id) & (
            #                                                                  db.Shares.company_id == Company.id)
            #                                                          ).filter(
            #     db.Company.stock_price.between(3, budget) & (
            #             func.coalesce(db.Shares.amount, 0) < ctx.api.overlord.max_stocks_owned)
            # ).order_by(func.random()).first()
            # TODO: make this choose companies like before, using the new query system
            query = select(Company)
            chosen_company = random.choice((await ctx.session.scalars(query)).all())

            if chosen_company:
                await buy.run(ctx, companies=[chosen_company], amount=budget)
            else:
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

    @api.command()
    async def test(ctx):
        if ctx.discord_message.author.id != 241244277382971399:
            return
        await ctx.send_message("Running")


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
