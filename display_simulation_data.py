import configparser

VERSION = 0


def display_top_points(section):
    section.pop('simulations')
    points_list = []
    for key in section.keys():
        value = section.getfloat(key)
        points_list.append((key, int(value)))
        # print(f'{key} {int(value):,} points')
    points_list.sort(key=lambda x: x[1], reverse=True)

    display_list = []
    for user_and_points in points_list:
        display_list.append(f'{user_and_points[0]}: {user_and_points[1]:,} points')

    for res in display_list:
        print(res)


def display_avg_per_strategy(section):
    section.pop('simulations')

    strategy_dict = {}
    for user in section.keys():
        strategy, _, active_hours = user.partition("|")
        points = int(section.getfloat(user))
        if strategy in strategy_dict:
            strategy_dict[strategy] += points
        else:
            strategy_dict[strategy] = points

    strategy_dict = dict(sorted(strategy_dict.items(), key=lambda x: x[1], reverse=True))

    for strategy, points in strategy_dict.items():
        print(f'{strategy}: {points:,} points avg')

# def display_peak_per_strategy(section):
#     section.pop("simulations")


def main():
    config = configparser.ConfigParser()
    config.read(f'simulation-data/{VERSION}.ini')
    for section_name in config.sections():
        section = config[section_name]
        print(f'########### Section: {section_name}')
        display_top_points(section)
        # display_avg_per_strategy(section)


if __name__ == '__main__':
    main()
