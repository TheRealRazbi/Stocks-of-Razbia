import overlord


def main():
    o = overlord.Overlord()
    o.display_credits()
    # overlord.start(overlord.iterate_forever_and_start_reading_chat(o), o)
    overlord.start(overlord.iterate_forever_read_chat_and_run_interface(o), o)


if __name__ == '__main__':
    main()















