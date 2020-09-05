from announcements import Announcement
from more_tools import BidirectionalMap

message_templates = {
    'stocks': '@{user_name} Minigame basic commands: !autoinvest, !introduction, !buy, !companies, !all commands, !my stats',
    'stocks_alias': 'stocks',
    'company_alias': 'company',
    'buy_successful': "@{user_name} just bought {amount} {stocks_alias} from [{company_abbv}] '{company_full_name}' for {cost} {currency_name}. "
                      "Now they gain {passive_income} {currency_name} from {company_abbv} each 10 mins. ",
    'buy_not_enough_points': '@{user_name} has {points} {currency_name} and requires {cost} aka {cost_minus_points} more.',
    # 'buy_0_stocks_remaining': '@{user_name} no {stocks_alias} left to buy at {company_abbv}.',
    # 'buy_not_enough_stocks_remaining': '@{user_name} tried buying {amount} {stocks_alias}, but only {remaining_shares} are remaining',
    'buy_or_sell_2_companies': '@{user_name} has inputted 2 of companies. You need to input a number and a {company_alias}.',
    'buy_or_sell_0_companies': "@{user_name} didn't input any {company_alias}. You need to input a number and a {company_alias}.",
    'sell_successful': "@{user_name} has sold {amount} {stocks_alias} from [{company_abbv}] '{company_full_name}' for {cost} {currency_name}. ",
    'sell_no_shares': "@{user_name} doesn't have any {stocks_alias} at {company_alias} {company_abbv}.",
    'sell_not_enough_shares': "@{user_name} doesn't have {amount} at {company_alias} {company_abbv} to sell them. "
                              "They have only {share_amount} {stocks_alias}.",
    'sell_everything_successful': '@{user_name} has sold {list_of_all_sells} for {total_outcome} {currency_name}.',
    'introduction': "@{user_name} This is a stock simulation minigame | '!stocks' for basic commands | "
                    "Buy stocks for passive income | "
                    "Naming Convention: Company[current_price, price_change] ",
    'company_first_time_tip': "@{user_name} Tip: The number on the left is the 'current price'. The one on the right is the 'price change'.",
    'no_shares': "@{user_name} doesn't have any shares. Use '!buy' to buy some.",
    'my_points': '@{user_name} currently has {user_points} {currency_name}',
    'my_stats': '@{user_name} '
                'Shares: {list_of_shares} ||| '
                'Income: {list_of_income} | Total Income: {total_income} {currency_name} per 10 mins ||| '
                'Profit: {raw_profit} {currency_name} | Profit Percentage: {percentage_profit}',
    'autoinvest_budget_too_small_for_companies': '@{user_name} too small budget. No {stocks_alias} bought.',
    'autoinvest_budget_too_small_for_available_points': '@{user_name} you need {budget} {currency_name}, '
                                                        'aka you need {budget_points_difference} more.',
    'about': '@{user_name} This minigame is open-source and it was made by Razbi and Nesami. '
             'Github link: https://github.com/TheRealRazbi/Stocks-of-Razbia',
    'company_released_product': "{company_full_name} just released a new product. Price it's likely to increase.",
}

# naming convention: command_names = {('new_name', group_name): 'og_name'}
command_names = BidirectionalMap({
    ('buy', None): 'buy',
    ('sell', None): 'sell',
    # ('income', 'my'): 'income',
    # ('my', None): 'my',
    # ('sell_everything', None): 'sell_everything',
    # ('all', None): 'all',
    # ('company', None): 'company',
    # ('companies', None): 'companies',
    ('stocks', None): 'stocks',
    ('stonks', None): 'stocks',
    # ('points', 'my'): 'points',
    ('mypoints', None): 'my points',
    # ('profit', 'my'): 'profit',
    ('myprofit', None): 'my profit',
    # ('income', 'my'): 'income',
    ('myincome', None): 'my income',
    # ('stats', 'my'): 'stats',
    ('mystats', None): 'my stats',
    # ('shares', 'my'): 'shares',
    ('myshares', None): 'my shares',
    ("mystats", None): "my stats",
    # ('month', 'next'): 'month',
    # ('autoinvest', None): 'autoinvest',
    # ('about', None): 'about',
    # ('introduction', None): 'introduction',
})

announcements = \
    {
        'element_list':
            [
                {
                    'name': 'stocks_or_stonks',
                    'contents': 'stonks | stocks',
                    'randomize_from': True
                },
                {
                    'name': 'commands',
                    'contents': "!introduction, !companies, !buy, !{stocks_or_stonks}, !autoinvest, !my income",
                    'randomize_from': False
                },
                {
                    'name': 'help_tip',
                    'contents': "Here are some commands to help you do that | " 
                                "Ughh maybe through these? | "
                                "I wonder what are these for | Commands | Turtles",
                    'randomize_from': True
                },
                {
                    'name': 'intro',
                    'contents': 'Wanna make some [currency_name] through stonks? | Be the master of stonks.',
                    'randomize_from': True
                },

            ],
        'result': '{intro} {help_tip}: {commands}'
    }


def load_message_templates():
    return message_templates


def load_command_names():
    return command_names


def load_announcements():
    return announcements



