from getpass import getpass
from termcolor import colored


def validate_input(message: str, character_min=0, hidden=False, requires_int=False, int_range=(1, 3), color=None):
    """
    :param message: The message the user will be shown
    :param character_min: The minimum amount of character for input to pass-through
    :param hidden: If enabled, it will use 'getpass' instead of 'input'
    :param requires_int: If enabled, it will force the input to be an int
    :param int_range: If requires_int enabled, it will make sure the input is in that range
    :return: validated User input
    """
    if not message.endswith(' '):
        message += ' '
    if color is not None:
        message = colored(message, color)
    while True:
        invalid = False
        if not hidden:
            res = input(message).strip()
        else:
            res = getpass(message).strip()
        if requires_int:
            try:
                res = int(res)
            except ValueError:
                continue
            for index_element, element in enumerate(int_range):
                if index_element == 0:
                    if res < element:
                        invalid = True
                elif index_element == 1:
                    if res > element:
                        invalid = True
        if invalid:
            continue

        if res is not None:
            if not requires_int:
                if len(res) >= character_min:
                    break
            else:
                break

    return res


if __name__ == '__main__':
    print(validate_input("Please input the token: ", requires_int=True, int_range=(1, 3)))



