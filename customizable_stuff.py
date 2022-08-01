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
    'buy_or_sell_2_companies': "@{user_name} has inputted 2 of companies. You need to input a number or 'all' and a {company_alias}.",
    'buy_or_sell_0_companies': "@{user_name} didn't input any {company_alias}. You need to input a number or 'all' and a {company_alias}.",
    'sell_successful': "@{user_name} has sold {amount} {stocks_alias} from [{company_abbv}] '{company_full_name}' for {cost} {currency_name}. ",
    'sell_no_shares': "@{user_name} doesn't have any {stocks_alias} at {company_alias} {company_abbv}.",
    'sell_not_enough_shares': "@{user_name} doesn't have {amount} at {company_alias} {company_abbv} needed to sell. "
                              "They have only {needed_amount} worth of {stocks_alias}.",
    'sell_everything_successful': '@{user_name} has sold {list_of_all_sells} for {total_outcome} {currency_name}.',
    'number_too_small': "@{user_name} has inputted a number too small. Only numbers above 0 work.",
    'budget_too_small': "@{user_name} has inputted a budget too small. 1 stock costs {company_price} {currency_name}. They only have {points} {currency_name}.",
    'reached_stocks_limit': "@{user_name} has reached the stocks limit of {stocks_limit} on company {company_abbv}.",
    'reached_stocks_limit_on_everything': "@{user_name} has reached the stocks limit of {stocks_limit} on all companies.",
    'introduction': "@{user_name} This is a stock simulation minigame | '!stocks' for basic commands | "
                    "Buy stocks for passive income | "
                    "Naming Convention: Company[current_price, price_change] ",
    'company_first_time_tip': "@{user_name} Tip: The number on the left is the 'current price'. The one on the right is the 'price change'.",
    'no_shares': "@{user_name} doesn't have any shares. Use '!buy' to buy some.",
    'my_points': '@{user_name} currently has {user_points} {currency_name}.',
    'my_stats': '@{user_name} '
                'Shares: {list_of_shares} ||| '
                'Income: {list_of_income} | Total Income: {total_income} {currency_name} per 10 mins ||| '
                'Profit: {raw_profit} {currency_name} | Profit Percentage: {percentage_profit}',
    'autoinvest_budget_too_small_for_companies': '@{user_name} too small budget. No {stocks_alias} bought.',
    'autoinvest_budget_too_small_for_available_points': '@{user_name} you need {budget} {currency_name}, '
                                                        'aka you need {budget_points_difference} more.',
    'company_released_product': "{company_summary} just released a new product. Price it's likely to increase.",
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
    ('points', 'my'): 'points',
    ('points', None): 'my points',
    # ('mypoints', None): 'my points',
    ('profit', 'my'): 'profit',
    ('profit', None): 'my profit',
    # ('myprofit', None): 'my profit',
    ('income', 'my'): 'income',
    ('income', None): 'my income',
    # ('myincome', None): 'my income',
    ('stats', 'my'): 'stats',
    ('stats', None): 'my stats',
    # ('mystats', None): 'my stats',
    ('shares', 'my'): 'shares',
    ('shares', None): 'my shares',
    # ('myshares', None): 'my shares',
    # ("mystats", None): "my stats",
    ('month', 'next'): 'month',
    ('month', None): 'next month',
    ('event', None): 'next event'
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
                    'name': 'help_tip',
                    'contents': "Here are some commands to help you do that | " 
                                "Maybe through these? | "
                                "I wonder what are these for | Commands | Turtles",
                    'randomize_from': True
                },
                {
                    'name': 'intro',
                    'contents': 'Wanna make some [currency_name] through stonks? | Be the master of stonks.',
                    'randomize_from': True
                },
                {
                    'name': 'variation1',
                    'contents': '{intro} {help_tip}: !introduction, !companies, !buy, !{stocks_or_stonks}, !autoinvest, !my income',
                    'randomize_from': False
                },
                {
                    'name': 'variation2',
                    'contents': '{intro}: For newcomers we got !autoinvest <number>',
                    'randomize_from': False
                },
                {
                    'name': 'one_of_the_2_variations',
                    'contents': '{variation1} | {variation2}',
                    'randomize_from': True
                },


            ],
        'result': '{one_of_the_2_variations}'
    }


def load_message_templates():
    return message_templates


def load_command_names():
    return command_names


def load_announcements():
    return announcements



