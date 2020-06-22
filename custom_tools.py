from getpass import getpass


def validate_input(message: str, character_min=0, hidden=False):
    """
    :param message: The message the user will be shown
    :param character_min: The minimum amount of character for input to pass-through
    :param hidden: If enabled, it will use 'getpass' instead of 'input'
    :return: validated User input
    """
    if not message.endswith(' '):
        message += ' '
    while True:
        if not hidden:
            res = input(message).strip()
        else:
            res = getpass(message).strip()
        if res is not None and len(res) >= character_min:
            break
    return res


if __name__ == '__main__':
    print(validate_input("Please input the token: "))



