def human_join_list(input_list: list, analyse_contents=False):
    if len(input_list) == 0:
        return ""
    elif len(input_list) == 1:
        return input_list[0]
    elif analyse_contents and " and " in input_list[-1]:
        return ", ".join(input_list)
    else:
        return " and ".join((", ".join(input_list[:-1]), input_list[-1]))